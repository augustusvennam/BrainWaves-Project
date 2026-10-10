from dataclasses import replace
import unittest
from unittest.mock import Mock, patch

import requests

from backend.config import Settings
from backend.services.cortex import CortexService
from backend.services.temi import TemiBridge
from backend.state import DashboardState
from test_cortex import ProtocolSocket


class ConnectivityTests(unittest.TestCase):
    def test_cortex_and_headset_have_independent_status(self):
        state = DashboardState()
        service = CortexService(replace(Settings.from_env(), client_id='test', client_secret='test'), state)
        socket = ProtocolSocket()
        socket.connected = False
        with patch('backend.services.cortex.websocket.create_connection', return_value=socket):
            self.assertFalse(service.connect_session())
        connections = state.snapshot()['connections']
        self.assertEqual(connections['cortex']['status'], 'connected')
        self.assertEqual(connections['headset']['status'], 'disconnected')
        service.close_session()
        self.assertEqual(state.snapshot()['connections']['cortex']['status'], 'disconnected')
        self.assertEqual(state.snapshot()['connections']['headset']['status'], 'unknown')

    def test_robot_status_requires_explicit_connection_report(self):
        bridge = TemiBridge('http://robot/api', 'test-token')
        for payload, expected in [({'robot_connected': True}, 'connected'),
                                  ({'robot_connected': False}, 'disconnected'),
                                  ({'ok': True}, 'unknown'),
                                  ({'robot_connected': 'true'}, 'unknown')]:
            with self.subTest(payload=payload), patch('backend.services.temi.requests.get', return_value=Mock(json=Mock(return_value=payload))) as get:
                self.assertEqual(bridge.check_connection()[0], expected)
                get.assert_called_once_with('http://robot/api/status', headers={'Authorization': 'Bearer test-token'}, timeout=3)

    def test_unconfigured_and_unreachable_robot(self):
        with patch('backend.services.temi.requests.get') as get:
            self.assertEqual(TemiBridge('', '').check_connection()[0], 'unconfigured')
            get.assert_not_called()
        with patch('backend.services.temi.requests.get', side_effect=requests.ConnectionError):
            self.assertEqual(TemiBridge('http://robot/api', '').check_connection()[0], 'unavailable')

    def test_v1_commands_exact_body_and_acknowledgement(self):
        bridge = TemiBridge('http://robot/api', 'test-token', DashboardState())
        def reply(url, **kwargs):
            return Mock(json=Mock(return_value={'id': kwargs['json']['id'], 'status': 'accepted'}))
        with patch('backend.services.temi.requests.post', side_effect=reply) as post:
            response = bridge.send('speak', {'text': 'Hello'})
            self.assertTrue(response['accepted'])
            post.assert_called_once_with('http://robot/api/commands',
                json={'id': response['id'], 'action': 'speak', 'payload': {'text': 'Hello'}},
                headers={'Authorization': 'Bearer test-token'}, timeout=3)
            self.assertEqual(bridge.state.commands[-1]['status'], 'accepted')
        with patch('backend.services.temi.requests.post', return_value=Mock(json=Mock(return_value={'status': 'completed'}))):
            with self.assertRaises(requests.RequestException):
                bridge.send('stop')
        self.assertEqual(bridge.state.commands[-1]['status'], 'failed')
