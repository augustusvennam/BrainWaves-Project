"""Protocol fixtures isolate hardware from acquisition, quality, and UI transport logic."""
import asyncio
import json
import queue
import threading
import time
import unittest
from unittest.mock import patch

from websockets import Request, Response, Headers
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.utils import accept_key

from src.config import load_config
from src.cortex_api_client import CortexClient, CortexError
from src.mood_determiner import MoodDeterminer
from src.temi_controller import TemiController
from src.websocket_server import EEGWebSocketServer, _accept_any_connection


class Socket:
    def __init__(self):
        self.frames = queue.Queue()
        self.receivers = set()

    def send(self, raw):
        request = json.loads(raw)
        self.frames.put(json.dumps({'id': request['id'], 'result': {
            'success': [{'streamName': 'met', 'cols': ['eng.isActive', 'eng', 'str']}], 'failure': []}}))
        self.frames.put(json.dumps({'sid': 'session', 'time': time.time(), 'met': [True, 0.8, 0.2]}))

    def recv(self):
        self.receivers.add(threading.get_ident())
        return self.frames.get(timeout=2)

    def close(self):
        self.frames.put('')


class ProtocolTests(unittest.TestCase):
    def client(self):
        client = CortexClient('test', 'test')
        client.session_id = 'session'
        return client

    def test_single_reader_installs_columns_before_first_packet(self):
        client = self.client()
        client.ws = Socket()
        client.is_connected = True
        seen = []
        event = threading.Event()
        client.register_handler('met', lambda packet: (seen.append(packet), event.set()))
        client._listener_thread = threading.Thread(target=client._listen_loop)
        client._listener_thread.start()
        try:
            self.assertTrue(client.subscribe(['met']))
            self.assertTrue(event.wait(1))
            self.assertEqual(seen[0]['met'], {'eng.isActive': True, 'eng': 0.8, 'str': 0.2})
            self.assertEqual(len(client.ws.receivers), 1)
            self.assertNotIn(threading.get_ident(), client.ws.receivers)
        finally:
            client.session_id = None
            client.close()

    def test_partial_subscription_is_failure(self):
        client = self.client()
        with patch.object(client, '_send_request', return_value={'result': {
                'success': [{'streamName': 'met', 'cols': ['eng']}],
                'failure': [{'streamName': 'pow', 'code': -1}]}}):
            self.assertFalse(client.subscribe(['met', 'pow']))
            self.assertEqual(client.subscription_failures[0]['streamName'], 'pow')

    def test_other_session_is_ignored_and_nested_device_values_decode(self):
        client = self.client()
        client.columns['dev'] = ['BatteryPercent', ['AF3', 'OVERALL']]
        seen = []
        client.register_handler('dev', seen.append)
        client._route({'sid': 'other', 'dev': [80, [4, 90]]})
        self.assertEqual(seen, [])
        client._route({'sid': 'session', 'dev': [80, [4, 90]]})
        self.assertEqual(seen[0]['dev']['sensors']['OVERALL'], 90)
        with self.assertRaises(CortexError):
            client._decode(['eng', 'str'], [0.5])

    def test_waits_for_approval_without_debit(self):
        client = self.client()
        with patch.object(client, '_send_request', side_effect=[
            {'result': {'accessGranted': False}}, {'result': {'accessGranted': True}},
            {'result': {'cortexToken': 'test-token'}}]) as send, patch('src.cortex_api_client.time.sleep'):
            self.assertTrue(client.authenticate())
            self.assertEqual(send.call_args_list[1].args[0], 'hasAccessRight')
            self.assertNotIn('debit', send.call_args_list[2].args[1])

    def test_rpc_error_is_not_success(self):
        client = self.client()
        client.is_connected = True
        class ErrorSocket:
            def send(_, raw):
                client._route({'id': json.loads(raw)['id'], 'error': {'code': -1, 'message': 'denied'}})
        client.ws = ErrorSocket()
        with self.assertRaisesRegex(CortexError, 'Cortex error -1'):
            client._send_request('subscribe')

    def test_temi_uses_unique_id_and_matches_completion(self):
        class TemiSocket:
            def __init__(self):
                self.command = None
                self.count = 0
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def settimeout(self, value): pass
            def send(self, message): self.command = json.loads(message)
            def recv(self):
                self.count += 1
                if self.count == 1: return 'Temi is ready to receive commands!'
                if self.count == 2: return json.dumps({'id': 'another-client'})
                return json.dumps({'id': self.command['id']})
        socket = TemiSocket()
        with patch('src.temi_controller.websocket.create_connection', return_value=socket):
            self.assertTrue(TemiController().speak('Hello'))
            self.assertEqual(socket.command['command'], 'speak')
            self.assertTrue(socket.command['id'])


class MoodTests(unittest.TestCase):
    def setUp(self):
        self.detector = MoodDeterminer()
        self.metrics = {'eng': 0.2, 'exc': 0.15, 'str': 0.1, 'rel': 0.9,
                        'rel.isActive': True, 'attention': 0.4}

    def sample(self, when):
        self.detector.update_quality({'overall': 90, 'sampleRateQuality': 1}, now=when)
        return self.detector.classify_from_metrics(self.metrics, now=when)

    def test_requires_enough_samples_and_stable_estimate(self):
        self.assertFalse(self.sample(0)['stable'])
        self.assertFalse(self.sample(10)['stable'])
        self.assertFalse(self.sample(20)['stable'])
        result = self.sample(30)
        self.assertTrue(result['stable'])
        self.assertEqual(result['primary_mood'], 'Relaxed')
        self.assertEqual(result['focus_level'], 0.4)
        self.assertNotIn('confidence', result)

    def test_null_inactive_and_boolean_are_rejected(self):
        for bad in (None, True, float('nan')):
            self.metrics['str'] = bad
            self.assertFalse(self.sample(0)['stable'])
        self.metrics['str'] = 0.1
        self.metrics['rel.isActive'] = False
        self.assertFalse(self.sample(10)['stable'])
        self.assertEqual(len(self.detector.history), 0)

    def test_quality_loss_and_stale_metric_clear_history(self):
        for when in (0, 10, 20, 30): self.sample(when)
        self.detector.update_quality({'overall': 20, 'sampleRateQuality': 1}, now=31)
        self.assertEqual(len(self.detector.history), 0)
        self.assertFalse(self.sample(40)['stable'])
        self.assertIsNotNone(self.detector.snapshot(now=70))
        self.assertEqual(len(self.detector.history), 0)


class BackendTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_browser_socket_gets_state_and_normalized_metrics(self):
        config = load_config()
        backend = EEGWebSocketServer(config)
        backend.client = CortexClient('test', 'test')
        backend.client.session_id = 'session'
        backend.state['cortex_connected'] = True
        worker = asyncio.create_task(backend.process())
        try:
            async with serve(backend.handler, '127.0.0.1', 0) as server:
                port = server.sockets[0].getsockname()[1]
                async with connect(f'ws://127.0.0.1:{port}') as socket:
                    initial = json.loads(await socket.recv())
                    self.assertEqual(initial['type'], 'state')
                    backend.queue.put_nowait(('met', {'sid': 'session', 'time': time.time(),
                        'met': {'eng': 0.7, 'exc': 0.1, 'str': 0.2, 'rel': None, 'rel.isActive': False}}))
                    message = json.loads(await asyncio.wait_for(socket.recv(), 1))
                    self.assertEqual(message['data']['eng'], 0.7)
                    self.assertIsNone(message['data']['rel'])
                    self.assertFalse(message['data']['assessment']['stable'])
                    backend.detector.history.append((1, {'rel': 0.9}))
                    await socket.send(json.dumps({'type': 'reset_assessment'}))
                    await socket.send(json.dumps({'type': 'ping'}))
                    self.assertEqual(json.loads(await socket.recv())['type'], 'pong')
                    self.assertEqual(len(backend.detector.history), 0)
                    self.assertEqual(backend.state['metrics'], {})
        finally:
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)

    async def test_old_source_samples_do_not_update_state(self):
        backend = EEGWebSocketServer(load_config())
        backend.client = CortexClient('test', 'test')
        backend.client.session_id = 'session'
        backend.state['cortex_connected'] = True
        worker = asyncio.create_task(backend.process())
        try:
            backend.queue.put_nowait(('met', {'sid': 'session', 'time': time.time()-60, 'met': {'eng': 0.9}}))
            await asyncio.sleep(0.01)
            self.assertEqual(backend.state['metrics'], {})
        finally:
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)

    def test_connection_header_without_upgrade_token_is_accepted(self):
        """Some stacks send 'Connection: keep-alive' on the upgrade request.
        The handshake must still succeed (101) rather than reject with 426."""
        import base64
        import os

        key = base64.b64encode(os.urandom(16)).decode()
        request = Request('/', Headers({
            'Upgrade': 'websocket',
            'Connection': 'keep-alive',
            'Sec-WebSocket-Key': key,
        }))
        response = _accept_any_connection(None, request)
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, 101)
        self.assertEqual(response.headers['Connection'], 'Upgrade')
        self.assertEqual(response.headers['Upgrade'], 'websocket')
        self.assertEqual(response.headers['Sec-WebSocket-Accept'], accept_key(key))

    def test_standard_connection_header_is_accepted(self):
        """A compliant 'Connection: Upgrade' request still works."""
        import base64
        import os

        key = base64.b64encode(os.urandom(16)).decode()
        request = Request('/', Headers({
            'Upgrade': 'websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Key': key,
        }))
        response = _accept_any_connection(None, request)
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, 101)

    def test_non_websocket_upgrade_is_rejected(self):
        """A request without Upgrade: websocket must fall back to the default
        handshake, which rejects it (no 101 response)."""
        import base64
        import os

        key = base64.b64encode(os.urandom(16)).decode()
        request = Request('/', Headers({
            'Upgrade': 'not-websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Key': key,
        }))
        self.assertIsNone(_accept_any_connection(None, request))

    def test_missing_websocket_key_is_rejected(self):
        """A request without Sec-WebSocket-Key must not be accepted."""
        request = Request('/', Headers({
            'Upgrade': 'websocket',
            'Connection': 'keep-alive',
        }))
        self.assertIsNone(_accept_any_connection(None, request))


if __name__ == '__main__':
    unittest.main()
