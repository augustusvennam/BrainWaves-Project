"""
Test script for Cortex API connectivity.
Run after setting up valid credentials in config/settings.yaml.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.cortex_api_client import CortexClient
from src.config import load_config
import time

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
        print("❌ Failed to connect to Cortex WebSocket server")
        return False
    
    print("✅ Connected to Cortex WebSocket server")
    
    if not client.authenticate():
        print("❌ Authentication failed - check credentials")
        client.close()
        return False
        
    print("✅ Authentication successful")
    
    headset_id = client.query_headset()
    if not headset_id:
        print("⚠️  No headset detected - ensure EPOC X is powered on and paired")
    else:
        print(f"✅ Headset detected: {headset_id}")
    
    client.close()
    print("✅ Connection test completed")
    return True

if __name__ == "__main__":
    test_cortex_connection()
