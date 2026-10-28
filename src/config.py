"""Non-secret YAML defaults plus local environment credentials."""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def load_config(config_path=None):
    load_dotenv(ROOT / '.env', override=False)
    path = Path(config_path) if config_path else ROOT / 'config/settings.yaml'
    with path.open(encoding='utf-8') as handle:
        config = yaml.safe_load(handle)
    config['emotiv'].update({
        'client_id': os.getenv('EMOTIV_CLIENT_ID', ''),
        'client_secret': os.getenv('EMOTIV_CLIENT_SECRET', ''),
        'ca_file': os.getenv('CORTEX_CA_FILE') or None,
        'headset_id': os.getenv('CORTEX_HEADSET_ID') or None,
    })
    config['temi']['robot_ip'] = os.getenv('TEMI_IP', config['temi']['robot_ip'])
    config['server']['host'] = os.getenv('SERVER_HOST', config['server']['host'])
    config['temi']['enabled'] = os.getenv('TEMI_ENABLED', '0') == '1'
    config['temi']['auto_speak'] = os.getenv('TEMI_AUTO_SPEAK', '0') == '1'
    return config


def cortex_from_config(config):
    from src.cortex_api_client import CortexClient
    settings = config['emotiv']
    if not settings['client_id'] or not settings['client_secret']:
        raise ValueError('Set EMOTIV_CLIENT_ID and EMOTIV_CLIENT_SECRET in .env. See .env.example.')
    return CortexClient(**{key: settings[key] for key in
                          ('client_id', 'client_secret', 'url', 'ca_file', 'headset_id')})
