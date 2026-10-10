"""Temi v1 command contract: SDK connection, acknowledgements and polled completion."""
import threading
import time
from uuid import uuid4

import requests



class TemiBridge:
    def __init__(self, url, token, state=None):
        self.url = url
        self.headers = {'Authorization': f'Bearer {token}'} if token else {}
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
            self.poll_commands()
            self.state.set_connection('temi', status, message)
            self.stop_event.wait(5)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=4)

    def poll_commands(self):
        if not self.state:
            return
        with self.state.lock:
            pending = [c.copy() for c in self.state.commands if c['status'] == 'accepted']
        for command in pending:
            try:
                response = requests.get(f"{self.url}/commands/{command['id']}", headers=self.headers, timeout=3)
                response.raise_for_status()
                update = response.json()
                if update.get('id') != command['id'] or update.get('status') not in ('accepted', 'completed', 'failed', 'cancelled'):
                    raise ValueError('Invalid command status.')
                status = update['status']
            except (requests.RequestException, ValueError):
                status = 'accepted'
            if status == 'accepted' and time.time() - command['time'] > 30:
                status = 'timed_out'
            with self.state.lock:
                for item in self.state.commands:
                    if item['id'] == command['id']:
                        if item['status'] != status:
                            item['status'] = status
                            self.state.event('Temi ' + item.get('action', 'command') + ': ' + status)

    def send(self, action, payload=None):
        if not self.url:
            raise RuntimeError('TEMI_BRIDGE_URL is not configured. Install a compatible Android bridge first.')
        if self.state and self.state.acquisition.replay:
            raise RuntimeError('Robot commands are disabled during Replay.')
        if action not in ('speak', 'stop', 'expression'):
            raise ValueError('Unsupported robot action.')
        command = {'id': str(uuid4()), 'action': action, 'payload': payload or {},
                   'time': time.time(), 'status': 'failed'}
        try:
            response = requests.post(f'{self.url}/commands', json={k: command[k] for k in ('id', 'action', 'payload')},
                                     headers=self.headers, timeout=3)
            response.raise_for_status()
            reply = response.json()
            if reply.get('id') != command['id'] or reply.get('status') != 'accepted':
                raise requests.RequestException('Bridge returned an invalid acknowledgement.')
            command['status'] = 'accepted'
        finally:
            if self.state:
                with self.state.lock:
                    self.state.commands.append(command)
                    self.state.event('Temi ' + action + ': ' + command['status'])
        return {'accepted': True, 'id': command['id'], 'status': 'accepted',
                'message': 'Bridge accepted the command; completion requires a bridge event.'}
