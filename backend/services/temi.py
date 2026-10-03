"""Optional real Android bridge integration. No automatic robot movement."""
import requests


class TemiBridge:
    def __init__(self, url, token):
        self.url = url
        self.headers = {'Authorization': f'Bearer {token}'} if token else {}

    def send(self, action, payload=None):
        if not self.url:
            raise RuntimeError('TEMI_BRIDGE_URL is not configured. Install a compatible Android bridge first.')
        response = requests.post(f'{self.url}/{action}', json=payload or {}, headers=self.headers, timeout=3)
        response.raise_for_status()
        return {'accepted': True, 'message': 'Bridge accepted the command; this does not confirm physical completion.'}
