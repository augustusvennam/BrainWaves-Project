"""Read local configuration once; keep credentials on the backend."""
from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
SUPPORTED_STREAMS = {'eeg', 'pow', 'com', 'met', 'dev', 'eq', 'sys', 'fac', 'mot'}


def positive_number(name: str, default: str) -> float:
    value = float(os.getenv(name, default))
    if not 0 < value < 3600:
        raise ValueError(f'{name} must be positive and less than 3600.')
    return value


@dataclass(frozen=True)
class Settings:
    client_id: str
    client_secret: str
    cortex_url: str
    ca_cert: str
    headset_id: str
    streams: tuple[str, ...]
    request_timeout: float
    reconnect_seconds: float
    activate_session: bool
    frontend_origin: str
    temi_url: str
    temi_token: str

    @classmethod
    def from_env(cls):
        url = os.getenv('CORTEX_URL', 'wss://localhost:6868')
        parsed = urlparse(url)
        if parsed.scheme != 'wss' or parsed.hostname not in {'localhost', '127.0.0.1', '::1'}:
            raise ValueError('CORTEX_URL must point to the local Cortex service using wss://.')
        streams = tuple(dict.fromkeys(s.strip() for s in os.getenv(
            'CORTEX_STREAMS', 'com,met,dev,eq,sys').split(',') if s.strip()))
        if not streams or not set(streams) <= SUPPORTED_STREAMS:
            raise ValueError('CORTEX_STREAMS must contain supported Cortex stream names.')
        activate = os.getenv('CORTEX_ACTIVATE_SESSION', 'false').lower()
        if activate not in {'true', 'false'}:
            raise ValueError('CORTEX_ACTIVATE_SESSION must be true or false.')
        return cls(
            os.getenv('EMOTIV_CLIENT_ID', '').strip(),
            os.getenv('EMOTIV_CLIENT_SECRET', '').strip(), url,
            os.getenv('CORTEX_CA_CERT', ''), os.getenv('CORTEX_HEADSET_ID', ''), streams,
            positive_number('CORTEX_REQUEST_TIMEOUT', '10'),
            positive_number('CORTEX_RECONNECT_SECONDS', '5'), activate == 'true',
            os.getenv('FRONTEND_ORIGIN', 'http://localhost:3000').rstrip('/'),
            os.getenv('TEMI_BRIDGE_URL', '').rstrip('/'), os.getenv('TEMI_BRIDGE_TOKEN', ''),
        )
