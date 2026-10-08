"""Main-branch Temi controller with a read-only bridge connection monitor."""
import threading

import requests

from backend.legacy.temi_controller import TemiController


class TemiBridge:
    def __init__(self, url, token, state=None):
        self.url = url
        self.headers = {'Authorization': f'Bearer {token}'} if token else {}
        self.controller = TemiController(mock=False, base_url=url, headers=self.headers)
        self.state = state
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, name='temi-status', daemon=True)

    def check_connection(self):
        if not self.url:
            return 'unconfigured', 'Set TEMI_BRIDGE_URL to connect your Temi Android bridge.'
        try:
            response = requests.get(f'{self.url}/status', headers=self.headers, timeout=3)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get('robot_connected'), bool):
                return 'unknown', 'Bridge reachable, but robot connection was not reported.'
            if data['robot_connected']:
                return 'connected', 'Temi bridge reports the robot connected.'
            return 'disconnected', 'Bridge reachable; Temi robot disconnected.'
        except (requests.RequestException, ValueError):
            return 'unavailable', 'Cannot verify Temi connection. Check the bridge URL and its /status endpoint.'

    def run(self):
        while not self.stop_event.is_set():
            status, message = self.check_connection()
            self.state.set_connection('temi', status, message)
            self.stop_event.wait(5)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=4)

    def send(self, action, payload=None):
        if not self.url:
            raise RuntimeError('TEMI_BRIDGE_URL is not configured. Install a compatible Android bridge first.')
        if action == 'speak':
            accepted = self.controller.speak((payload or {})['text'])
        elif action == 'stop':
            accepted = self.controller.stop_movement()
        else:
            raise ValueError('Unsupported robot action.')
        if not accepted:
            raise requests.RequestException('Temi bridge unreachable or rejected the command.')
        return {'accepted': True, 'message': 'Bridge accepted the command; this does not confirm physical completion.'}
