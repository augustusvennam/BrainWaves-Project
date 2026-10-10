import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.app import app, settings, state


class LocalTransportTests(unittest.TestCase):
    def setUp(self):
        state.reset_session()
        state.set_status('waiting_headset', 'Test fixture: no physical headset.')
        self.client = TestClient(app)

    def test_health_and_snapshot_without_hardware(self):
        self.assertEqual(self.client.get('/api/health').status_code, 200)
        self.assertTrue(self.client.get('/api/health').json()['ok'])
        self.assertEqual(self.client.get('/api/snapshot').json()['eeg'], [])

    def test_websocket_stream_data_disconnect_and_reconnect(self):
        state.session_id = 'fixture'
        state.subscribe({'success': [{'streamName': 'eeg', 'cols': ['AF3']}]})
        state.receive({'sid': 'fixture', 'time': 1, 'eeg': [4200]})
        with self.client.websocket_connect('/api/live', headers={'origin': settings.frontend_origin}) as socket:
            data = socket.receive_json()
            self.assertEqual(data['eeg'][0]['values']['AF3'], 4200)
        state.reset_session()
        state.set_status('disconnected', 'Fixture disconnected.')
        with self.client.websocket_connect('/api/live') as socket:
            self.assertEqual(socket.receive_json()['eeg'], [])

    def test_wrong_origin_is_rejected(self):
        from starlette.websockets import WebSocketDisconnect
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect('/api/live', headers={'origin': 'https://other.example'}):
                pass
        self.assertEqual(self.client.post('/api/temi/stop', headers={'origin': 'https://other.example'}).status_code, 403)

    def test_optional_robot_errors_and_validation(self):
        with patch('backend.app.temi.url', ''):
            self.assertEqual(self.client.post('/api/temi/stop').status_code, 503)
        self.assertEqual(self.client.post('/api/temi/speak', json={'text': ''}).status_code, 422)

    def test_participant_routes_gate_data_and_preserve_cortex_session(self):
        state.session_id = 'existing-cortex'
        with patch('backend.app.cortex.submit') as submit:
            self.assertEqual(self.client.post('/api/session', json={'action':'start'}).status_code, 200)
            self.assertEqual(self.client.post('/api/session', json={'action':'assess'}).status_code, 409)
            self.assertEqual(self.client.post('/api/session', json={'action':'baseline'}).status_code, 200)
            self.assertEqual(state.participant.phase, 'baseline')
            self.assertEqual(self.client.post('/api/session', json={'action':'confirm'}).status_code, 409)
            self.assertEqual(self.client.post('/api/session', json={'action':'end'}).status_code, 200)
            submit.assert_not_called()
        self.assertEqual(state.session_id, 'existing-cortex')
        state.event('Real route test activity')
        self.assertEqual(self.client.post('/api/events/clear').status_code, 200)
        self.assertEqual(list(state.events), [])

    def test_recording_consent_replay_blocks_robot_and_profiles(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp, patch('backend.acquisition.ROOT', Path(temp)):
            self.client.post('/api/session', json={'action':'start'})
            self.assertEqual(self.client.post('/api/recording', json={'action':'start'}).status_code, 409)
            self.assertEqual(self.client.post('/api/recording', json={'action':'start', 'consent':True}).status_code, 200)
            name = state.acquisition.path
            self.client.post('/api/recording', json={'action':'stop'})
            self.client.post('/api/session', json={'action':'end'})
            self.assertEqual(self.client.post('/api/recording', json={'action':'replay','file':name}).status_code, 200)
            with patch('backend.app.temi.send') as send, patch('backend.app.cortex.submit') as submit:
                self.assertEqual(self.client.post('/api/temi/speak', json={'text':'Test'}).status_code, 503)
                self.assertEqual(self.client.post('/api/profile', json={'operation':'load','profile':'Test'}).status_code, 409)
                send.assert_not_called()
                submit.assert_not_called()
            self.assertEqual(self.client.post('/api/recording', json={'action':'exit_replay'}).status_code, 200)
            self.assertFalse(state.acquisition.snapshot()['replay'])
