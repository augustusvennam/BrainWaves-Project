"""Cortex JSON-RPC client. One reader owns the socket; callbacks never call RPC."""
import json
import logging
import queue
import ssl
import threading
import time

import websocket

log = logging.getLogger(__name__)
STREAMS = ('met', 'pow', 'dev', 'eq', 'com', 'fac', 'mot', 'sys', 'eeg')


class CortexError(RuntimeError):
    pass


class CortexClient:
    def __init__(self, client_id, client_secret, url='wss://localhost:6868',
                 ca_file=None, headset_id=None, approval_timeout=120):
        self.client_id, self.client_secret = client_id, client_secret
        self.url, self.ca_file = url, ca_file
        self.preferred_headset = headset_id
        self.approval_timeout = approval_timeout
        self.ws = None
        self.auth_token = self.session_id = self.headset_id = None
        self.is_connected = False
        self.message_handlers, self.columns, self.subscription_failures = {}, {}, []
        self._pending, self._counter = {}, 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._listener_thread = None
        # Stream samples can arrive before the subscribing RPC returns to its caller.
        self._subscribe_requested = []

    def connect(self):
        sslopt = {'cert_reqs': ssl.CERT_REQUIRED, 'check_hostname': True}
        if self.ca_file:
            sslopt['ca_certs'] = self.ca_file
        try:
            self.ws = websocket.create_connection(self.url, sslopt=sslopt, timeout=10)
            self.ws.settimeout(None)
            self.is_connected = True
            self._stop.clear()
            self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._listener_thread.start()
            return True
        except Exception as exc:
            log.error('Cortex connection failed (%s). Check Launcher and CORTEX_CA_FILE.', type(exc).__name__)
            return False

    def _send_request(self, method, params=None):
        if not self.is_connected:
            raise CortexError('Cortex is disconnected')
        with self._lock:
            self._counter += 1
            req_id, response = self._counter, queue.Queue()
            self._pending[req_id] = response
        try:
            self.ws.send(json.dumps({'jsonrpc': '2.0', 'id': req_id,
                                     'method': method, 'params': params or {}}))
            try:
                message = response.get(timeout=15)
            except queue.Empty as exc:
                raise CortexError(f'{method}: response timeout') from exc
            if isinstance(message, Exception):
                raise message
            if 'error' in message:
                error = message['error']
                # No request parameters or tokens are included in logs.
                raise CortexError(f'{method}: Cortex error {error.get("code")}: {error.get("message")}')
            return message
        finally:
            with self._lock:
                self._pending.pop(req_id, None)

    def authenticate(self):
        credentials = {'clientId': self.client_id, 'clientSecret': self.client_secret}
        result = self._send_request('requestAccess', credentials).get('result', {})
        deadline = time.monotonic() + self.approval_timeout
        if not result.get('accessGranted'):
            log.info('Approve this application in EMOTIV Launcher (waiting up to %ss).', self.approval_timeout)
        while not result.get('accessGranted'):
            if time.monotonic() >= deadline:
                raise CortexError('App approval timed out. Approve access in Launcher and retry.')
            time.sleep(1)
            result = self._send_request('hasAccessRight', credentials).get('result', {})
        result = self._send_request('authorize', credentials).get('result', {})
        if result.get('warning'):
            log.warning('Cortex authorization warning code: %s. Check Launcher/EULA.', result['warning'].get('code'))
        self.auth_token = result.get('cortexToken')
        if not self.auth_token:
            raise CortexError('Authorization returned no token')
        return True

    def query_headset(self, timeout=20):
        self._send_request('controlDevice', {'command': 'refresh'})
        deadline = time.monotonic() + timeout
        selected = None
        while time.monotonic() < deadline:
            headsets = self._send_request('queryHeadsets').get('result', [])
            if self.preferred_headset:
                headsets = [h for h in headsets if h['id'] == self.preferred_headset]
            # Never silently select a virtual device for a physical demonstration.
            else:
                headsets = [h for h in headsets if 'virtual' not in h['id'].lower()]
            if len(headsets) > 1:
                raise CortexError('Multiple headsets found. Set CORTEX_HEADSET_ID explicitly.')
            if headsets:
                selected = headsets[0]
                if selected.get('status') == 'connected':
                    self.headset_id = selected['id']
                    return self.headset_id
                if selected.get('connectedBy') == 'usb':
                    raise CortexError('Use the wireless receiver or BLE, not a USB charging cable')
                if selected.get('status') == 'discovered':
                    self._send_request('controlDevice', {'command': 'connect', 'headset': selected['id']})
            time.sleep(1)
        raise CortexError('No connected headset. Check receiver/BLE and Launcher.')

    def create_session(self, status='open'):
        result = self._send_request('createSession', {
            'cortexToken': self.auth_token, 'headset': self.headset_id, 'status': status
        }).get('result', {})
        self.session_id = result.get('id')
        if not self.session_id:
            raise CortexError('Session creation returned no id')
        return True

    def register_handler(self, stream, handler):
        self.message_handlers[stream] = handler

    def subscribe(self, streams, handlers=None):
        if handlers:
            self.message_handlers.update(handlers)
        self._subscribe_requested = list(streams)
        result = self._send_request('subscribe', {
            'cortexToken': self.auth_token, 'session': self.session_id, 'streams': streams
        }).get('result', {})
        self.subscription_failures = result.get('failure', [])
        succeeded = {s['streamName'] for s in result.get('success', [])}
        return set(streams).issubset(succeeded)

    @staticmethod
    def _decode(cols, values):
        if not isinstance(values, list) or len(cols) != len(values):
            raise CortexError('Stream sample does not match subscription columns')
        result = {}
        for col, value in zip(cols, values):
            if isinstance(col, list):
                result['sensors'] = CortexClient._decode(col, value)
            else:
                result[col] = value
        return result

    def _route(self, data):
        if not isinstance(data, dict):
            return
        if 'id' in data:
            # Install metadata on the socket reader BEFORE processing subsequent samples.
            for item in data.get('result', {}).get('success', []) if isinstance(data.get('result'), dict) else []:
                self.columns[item['streamName']] = item['cols']
            with self._lock:
                response = self._pending.get(data['id'])
            if response is not None:
                response.put(data)
            return
        if data.get('sid') != self.session_id:
            return
        for stream in STREAMS:
            if stream in data and stream in self.message_handlers and stream in self.columns:
                try:
                    decoded = self._decode(self.columns[stream], data[stream])
                    self.message_handlers[stream]({**data, stream: decoded})
                except Exception:
                    log.exception('Could not process %s sample', stream)

    def _listen_loop(self):
        try:
            while not self._stop.is_set():
                raw = self.ws.recv()
                if not raw:
                    break
                self._route(json.loads(raw))
        except Exception:
            if not self._stop.is_set():
                log.warning('Cortex socket closed unexpectedly')
        finally:
            self.is_connected = False
            with self._lock:
                for response in self._pending.values():
                    response.put(CortexError('Cortex socket closed'))

    def close(self):
        try:
            if self.is_connected and self.session_id:
                self._send_request('updateSession', {'cortexToken': self.auth_token,
                                                     'session': self.session_id, 'status': 'close'})
        except Exception:
            log.warning('Session could not be closed cleanly')
        finally:
            self._stop.set()
            if self.ws:
                self.ws.close()
            if self._listener_thread and self._listener_thread is not threading.current_thread():
                self._listener_thread.join(timeout=2)
            self.is_connected = False
            self.session_id = None
