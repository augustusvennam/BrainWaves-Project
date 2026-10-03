"""
Test script for Cortex API connectivity.
Run after setting up valid credentials in config/settings.yaml.

Exits non-zero on any failure so CI can detect a broken Cortex setup.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.cortex_api_client import CortexClient
from src.config import load_config


def fail(message):
    print(f"❌ FATAL: {message}")
    sys.exit(1)


def test_cortex_connection():
    print("Testing Cortex API connection...")
    config = load_config()
    emotiv_cfg = config["emotiv"]

    client = CortexClient(
        client_id=emotiv_cfg["client_id"],
        client_secret=emotiv_cfg["client_secret"],
        url=emotiv_cfg["websocket_url"]
    )

    if not client.connect():
        fail("Could not connect to Cortex WebSocket server at "
             f"{emotiv_cfg['websocket_url']}. Is Cortex running?")

    print("✅ Connected to Cortex WebSocket server")

    if not client.authenticate():
        fail("Authentication failed — check credentials in config/settings.yaml")
    print("✅ Authentication successful")

    headset_id = client.query_headset()
    if not headset_id:
        fail("No headset detected — ensure EPOC X is powered on and paired")
    print(f"✅ Headset detected: {headset_id}")

    if not client.create_session():
        fail("Could not create recording session")
    print(f"✅ Session created: {client.session_id}")

    if not client.subscribe(['com', 'met', 'sys']):
        fail("Could not subscribe to data streams")
    print("✅ Subscribed to streams: com, met, sys")

    client.close()
    print("✅ Connection test completed")
    return True


if __name__ == "__main__":
    test_cortex_connection()