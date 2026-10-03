from collections import deque
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from backend.config import Settings
from backend.services.cortex import CortexError, CortexService
from backend.state import DashboardState


class ProtocolSocket:
    """Test fixture only: answers protocol requests without a physical headset."""
    def __init__(self):
        self.messages = deque()
        self.methods = []
        self.requests = []
        self.closed = False
        self.connected = True

    def settimeout(self, timeout):
        pass

    def send(self, raw):
        request = json.loads(raw)
        method = request['method']
        self.methods.append(method)
        self.requests.append(request)
        results = {
            'requestAccess': {'accessGranted': True}, 'authorize': {'cortexToken': 'test-token'},
            'queryHeadsets': [{'id': 'test-headset', 'status': 'connected' if self.connected else 'disconnected'}],
            'createSession': {'id': 'test-session'},
            'subscribe': {'success': [{'streamName': 'eeg', 'cols': ['COUNTER', 'AF3']}],
                          'failure': [{'streamName': 'pow', 'message': 'License denied'}]},
            'updateSession': {'status': 'closed'},
        }
        if method == 'subscribe':
            # A notification arriving before the reply must not be mistaken for the reply.
            self.messages.append({'sid': 'test-session', 'time': 100, 'eeg': [1, 4201]})
        self.messages.append({'jsonrpc': '2.0', 'id': request['id'], 'result': results[method]})

    def recv(self):
        if self.messages:
            return json.dumps(self.messages.popleft())
        import websocket
        raise websocket.WebSocketTimeoutException()

    def close(self):
        self.closed = True


class CortexTests(unittest.TestCase):
    def setUp(self):
        self.settings = replace(Settings.from_env(), client_id='test-id', client_secret='test-secret', streams=('eeg', 'pow'), activate_session=True)
        self.state = DashboardState()
        self.service = CortexService(self.settings, self.state)
        self.socket = ProtocolSocket()

    def test_protocol_handshake_and_interleaved_sample(self):
        with patch('backend.services.cortex.websocket.create_connection', return_value=self.socket):
            self.assertTrue(self.service.connect_session())
        self.assertEqual(self.socket.methods, ['requestAccess', 'queryHeadsets', 'authorize', 'createSession', 'subscribe'])
        self.assertEqual(self.state.snapshot()['eeg'][0]['values']['AF3'], 4201)
        self.assertEqual(self.state.status['phase'], 'streaming')
        self.assertEqual(self.socket.requests[2]['params']['debit'], 1)
        self.assertEqual(self.socket.requests[3]['params']['status'], 'active')
        self.service.close_session()
        self.assertTrue(self.socket.closed)
        self.assertEqual(self.socket.methods[-1], 'updateSession')

    def test_no_headset_waits_without_creating_session(self):
        self.socket.connected = False
        with patch('backend.services.cortex.websocket.create_connection', return_value=self.socket):
            self.assertFalse(self.service.connect_session())
        self.assertEqual(self.state.status['phase'], 'waiting_headset')
        self.assertNotIn('createSession', self.socket.methods)
        self.service.close_session()

    def test_error_reply_is_not_success(self):
        self.service.ws = self.socket
        with patch.object(self.socket, 'send', side_effect=lambda _: self.socket.messages.append(
            {'id': 1, 'error': {'code': -32000, 'message': 'secret should not be exposed'}})):
            with self.assertRaisesRegex(CortexError, 'code -32000') as error:
                self.service.request('authorize')
        self.assertNotIn('secret should not be exposed', str(error.exception))

    def test_retry_resets_session(self):
        count = 0

        def connect():
            nonlocal count
            count += 1
            if count == 1:
                self.state.session_id = 'old'
                raise CortexError('Disconnected during test.')
            self.assertIsNone(self.state.session_id)
            self.service.stop_event.set()
            return False

        with patch.object(self.service, 'connect_session', side_effect=connect), patch.object(self.service.stop_event, 'wait'):
            self.service.run()
        self.assertEqual(count, 2)

    def test_missing_credentials_keeps_backend_available(self):
        service = CortexService(replace(self.settings, client_id='', client_secret=''), self.state)
        service.run()
        self.assertEqual(self.state.status['phase'], 'waiting_credentials')

    def test_shutdown_closes_active_session(self):
        with patch('backend.services.cortex.websocket.create_connection', return_value=self.socket):
            self.service.connect_session()
        self.service.stop_event.set()
        self.service.close_session()
        self.assertEqual(self.socket.methods[-1], 'updateSession')
        self.assertTrue(self.socket.closed)

    def test_basic_session_does_not_debit_license(self):
        self.service.settings = replace(self.settings, activate_session=False)
        with patch('backend.services.cortex.websocket.create_connection', return_value=self.socket):
            self.service.connect_session()
        self.assertNotIn('debit', self.socket.requests[2]['params'])
        self.assertEqual(self.socket.requests[3]['params']['status'], 'open')
        self.service.close_session()
