"""One socket owner handles both JSON-RPC replies and streaming notifications."""
from collections import deque
import json
import logging
import ssl
import threading
import time

import websocket

from backend.legacy.cortex_api_client import CortexClient

logger = logging.getLogger(__name__)


class CortexError(RuntimeError):
    pass


class CortexService:
    def __init__(self, settings, state):
        self.settings = settings
        self.state = state
        self.stop_event = threading.Event()
        self.ws = None
        self.counter = 0
        self.pending = deque(maxlen=1024)
        self.token = None
        self.thread = threading.Thread(target=self.run, name='cortex', daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=self.settings.request_timeout + 2)
        if self.thread.is_alive() and self.ws:
            self.ws.close()
            self.thread.join(timeout=2)

    def request(self, method, params=None, *, allow_shutdown=False):
        self.counter += 1
        request_id = self.counter
        self.ws.send(json.dumps({'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params or {}}))
        deadline = time.monotonic() + self.settings.request_timeout
        while (allow_shutdown or not self.stop_event.is_set()) and time.monotonic() < deadline:
            try:
                message = self.read_message()
            except websocket.WebSocketTimeoutException:
                continue
            if message.get('id') != request_id:
                self.pending.append(message)
                continue
            if 'error' in message:
                error = message['error']
                # Log only the error code; payloads can contain credentials or tokens.
                raise CortexError(f'Cortex {method} failed (code {error.get("code", "unknown")}). Check Launcher access and your license.')
            return message.get('result', {})
        raise CortexError(f'Cortex {method} timed out. Check Emotiv Launcher.')

    def read_message(self):
        raw = self.ws.recv()
        if not raw:
            raise CortexError('Cortex connection closed.')
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object.')
            return data
        except (ValueError, TypeError):
            with self.state.lock:
                self.state.invalid_samples += 1
            return {}

    def drain_pending(self):
        while self.pending:
            self.state.receive(self.pending.popleft())

    def connect_session(self):
        self.state.set_connection('cortex', 'connecting', 'Connecting to local Cortex API.')
        self.state.set_status('connecting', 'Connecting to local Emotiv Cortex.')
        tls = {'cert_reqs': ssl.CERT_REQUIRED, 'ca_certs': self.settings.ca_cert} if self.settings.ca_cert else {'cert_reqs': ssl.CERT_NONE}
        client = CortexClient(self.settings.client_id, self.settings.client_secret, self.settings.cortex_url)
        if not client.connect(timeout=self.settings.request_timeout, sslopt=tls):
            raise CortexError('Cannot connect to local Cortex. Open Emotiv Launcher; retrying automatically.')
        self.ws = client.ws
        self.state.set_connection('cortex', 'connected', 'Local Cortex API connected.')
        self.ws.settimeout(1)
        access = self.request('requestAccess', {
            'clientId': self.settings.client_id, 'clientSecret': self.settings.client_secret,
        })
        if not access.get('accessGranted'):
            raise CortexError('Approve BrainWaves access in Emotiv Launcher, then wait for retry.')
        headsets = self.request('queryHeadsets')
        candidates = [h for h in headsets if h.get('status') == 'connected' and (
            not self.settings.headset_id or h.get('id') == self.settings.headset_id)]
        if not candidates:
            self.state.set_connection('headset', 'disconnected', 'No connected headset found in Cortex.')
            self.state.set_status('waiting_headset', 'No connected headset. Pair it in Emotiv Launcher; retrying automatically.')
            return False
        self.state.set_connection('headset', 'connected', f"Headset {candidates[0]['id']} connected.")
        auth_params = {'clientId': self.settings.client_id, 'clientSecret': self.settings.client_secret}
        if self.settings.activate_session:
            # Activated sessions may consume the user's licensed session quota.
            auth_params['debit'] = 1
        auth = self.request('authorize', auth_params)
        self.token = auth.get('cortexToken')
        if not self.token:
            raise CortexError('Cortex did not return an authorization token.')
        headset = candidates[0]
        session = self.request('createSession', {
            'cortexToken': self.token, 'headset': headset['id'], 'status': 'active' if self.settings.activate_session else 'open',
        })
        if not session.get('id'):
            raise CortexError('Cortex did not create a headset session.')
        with self.state.lock:
            self.state.headset = {'id': headset['id'], 'status': headset['status']}
            self.state.session_id = session['id']
        result = self.request('subscribe', {
            'cortexToken': self.token, 'session': session['id'], 'streams': list(self.settings.streams),
        })
        self.state.subscribe(result)
        if not self.state.schemas:
            raise CortexError('All requested streams were denied. Check CORTEX_STREAMS and your license.')
        self.drain_pending()
        self.state.set_status('streaming', 'Headset connected. Displaying available live Cortex streams.')
        return True

    def listen(self):
        next_check = time.monotonic() + 5
        while not self.stop_event.is_set():
            try:
                self.state.receive(self.read_message())
            except websocket.WebSocketTimeoutException:
                pass
            if time.monotonic() >= next_check:
                headsets = self.request('queryHeadsets')
                self.drain_pending()
                if not any(h.get('id') == self.state.headset['id'] and h.get('status') == 'connected' for h in headsets):
                    raise CortexError('Headset disconnected. Reconnect it in Emotiv Launcher; retrying automatically.')
                next_check = time.monotonic() + 5

    def close_session(self):
        if self.ws:
            try:
                if self.state.session_id and self.token:
                    self.request('updateSession', {'cortexToken': self.token, 'session': self.state.session_id, 'status': 'close'}, allow_shutdown=True)
            except Exception:
                pass
            self.ws.close()
        self.ws = None
        self.token = None
        self.pending.clear()
        self.state.set_connection('cortex', 'disconnected', 'Cortex socket closed; waiting for retry.')
        self.state.set_connection('headset', 'unknown', 'Headset connection cannot be verified while Cortex is disconnected.')

    def run(self):
        if not self.settings.client_id or not self.settings.client_secret:
            self.state.set_connection('cortex', 'unconfigured', 'Set Emotiv credentials in .env to connect.')
            self.state.set_status('waiting_credentials', 'Set EMOTIV_CLIENT_ID and EMOTIV_CLIENT_SECRET in .env, then restart the backend.')
            return
        while not self.stop_event.is_set():
            try:
                if self.connect_session():
                    self.listen()
            except CortexError as error:
                self.state.set_status('disconnected', str(error))
            except Exception as error:
                logger.warning('Cortex connection failed: %s', type(error).__name__)
                self.state.set_status('error', 'Cannot communicate with local Cortex. Check Launcher, credentials, headset, and certificate settings; retrying automatically.')
            finally:
                self.close_session()
                self.state.reset_session()
            self.stop_event.wait(self.settings.reconnect_seconds)
