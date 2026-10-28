"""Speech-only client for the linked Temi Wizard-of-Oz app."""
import json
import time
import uuid

import websocket


class TemiController:
    def __init__(self, robot_ip='192.168.1.100', port=8175, timeout_s=30):
        self.url = f'ws://{robot_ip}:{port}'
        self.timeout_s = timeout_s

    def is_connected(self):
        """websocket-client 1.9.2's WebSocket is not a context manager, so open
        the socket explicitly and close it in a finally block."""
        ws = None
        try:
            ws = websocket.create_connection(self.url, timeout=5)
            return ws.recv() == 'Temi is ready to receive commands!'
        except (OSError, websocket.WebSocketException):
            return False
        finally:
            if ws is not None:
                ws.close()

    def speak(self, text):
        """Keep the socket open until TTS completion; sending is not completion."""
        command_id = str(uuid.uuid4())
        ws = websocket.create_connection(self.url, timeout=5)
        try:
            if ws.recv() != 'Temi is ready to receive commands!':
                raise RuntimeError('Unexpected Temi greeting')
            ws.send(json.dumps({'command': 'speak', 'sentence': text, 'id': command_id}))
            deadline = time.monotonic() + self.timeout_s
            while time.monotonic() < deadline:
                ws.settimeout(max(0.1, deadline - time.monotonic()))
                message = ws.recv()
                if not message:
                    break
                if isinstance(message, str):
                    try:
                        result = json.loads(message)
                    except ValueError:
                        continue
                    # RobotApi.onTtsStatusChanged broadcasts {id: speak_id} on completion.
                    if isinstance(result, dict) and result.get('id') == command_id:
                        return True
            raise TimeoutError('Temi did not acknowledge speech completion')
        finally:
            ws.close()

    def open_url(self, url):
        """Load a URL on the Temi screen via the WOZ app's openURL command."""
        ws = websocket.create_connection(self.url, timeout=5)
        try:
            if ws.recv() != 'Temi is ready to receive commands!':
                raise RuntimeError('Unexpected Temi greeting')
            ws.send(json.dumps({'command': 'openURL', 'url': url}))
        finally:
            ws.close()
