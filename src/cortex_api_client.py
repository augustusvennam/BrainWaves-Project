"""
Emotiv Cortex API v2 WebSocket Client Wrapper.
Handles authentication, session creation, mental command & performance metric subscriptions.

CRITICAL NOTES (from review):
- Only connects to wss://localhost:6868 (local Cortex service). No remote endpoint.
- Uses self-signed certificate — must disable cert verification.
- Streams available: com, met, fac, mot, sys, eeg (raw requires premium license)
- Performance metrics include: eng, exc, str, rel, int, lex
- Signal quality via 'eq' or 'dev' streams
- Mental commands require 'neutral' baseline training first
"""
import json
import ssl
import time
import threading
import websocket

class CortexClient:
    def __init__(self, client_id, client_secret, url="wss://localhost:6868"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.url = url
        self.ws = None
        self.auth_token = None
        self.session_id = None
        self.headset_id = None
        self.is_connected = False
        self.message_handlers = {}
        self._req_counter = 0

    def connect(self):
        """Connect to local Cortex WebSocket server.
        Cortex runs locally at wss://localhost:6868 with a self-signed certificate.
        """
        print(f"[CortexClient] Connecting to {self.url}...")
        try:
            self.ws = websocket.create_connection(
                self.url,
                sslopt={"cert_reqs": ssl.CERT_NONE}  # Self-signed cert
            )
            self.is_connected = True
            print("[CortexClient] Connected successfully.")
            return True
        except Exception as e:
            print(f"[CortexClient] Connection failed: {e}")
            self.is_connected = False
            return False

    def _send_request(self, method, params=None):
        """Send JSON-RPC request and return parsed response."""
        self._req_counter += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self._req_counter
        }
        self.ws.send(json.dumps(payload))
        resp = self.ws.recv()
        return json.loads(resp)

    def authenticate(self):
        """Perform full handshake: check info, request access, get auth token."""
        print("[CortexClient] Authenticating with Cortex...")
        
        # 1. Request access
        req_acc = self._send_request("requestAccess", {
            "clientId": self.client_id,
            "clientSecret": self.client_secret
        })
        
        # 2. Authorize
        auth_resp = self._send_request("authorize", {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
            "debit": 1
        })
        
        if "result" in auth_resp and "cortexToken" in auth_resp["result"]:
            self.auth_token = auth_resp["result"]["cortexToken"]
            print(f"[CortexClient] Authenticated successfully. Token acquired.")
            return True
        else:
            print(f"[CortexClient] Auth failed: {auth_resp}")
            return False

    def query_headset(self):
        """Scan for connected EPOC X or virtual headset."""
        resp = self._send_request("queryHeadsets", {})
        headsets = resp.get("result", [])
        if headsets:
            self.headset_id = headsets[0]["id"]
            print(f"[CortexClient] Found headset: {self.headset_id} ({headsets[0].get('status')})")
            return self.headset_id
        print("[CortexClient] No headset found.")
        return None

    def create_session(self, status="active"):
        """Create an active recording/stream session."""
        if not self.headset_id or not self.auth_token:
            print("[CortexClient] Missing headset_id or auth_token.")
            return False
        resp = self._send_request("createSession", {
            "cortexToken": self.auth_token,
            "headset": self.headset_id,
            "status": status
        })
        if "result" in resp and "id" in resp["result"]:
            self.session_id = resp["result"]["id"]
            print(f"[CortexClient] Session created: {self.session_id}")
            return True
        print(f"[CortexClient] Failed to create session: {resp}")
        return False

    def subscribe(self, streams, callback):
        """Subscribe to data streams (e.g. ['com', 'met', 'fac', 'sys']) with live callback.
        
        Available streams:
        - com: Mental Commands (requires training 'neutral' first)
        - met: Performance Metrics (eng, exc, str, rel, int, lex)
        - fac: Facial Expressions (blink, smile, clench, eyebrow raise)
        - mot: Motion Data (9-axis IMU)
        - sys: System Events (headset status, training events, signal quality)
        - eeg: Raw EEG (requires premium license)
        """
        if not self.session_id or not self.auth_token:
            print("[CortexClient] Missing active session.")
            return False
            
        resp = self._send_request("subscribe", {
            "cortexToken": self.auth_token,
            "session": self.session_id,
            "streams": streams
        })
        
        print(f"[CortexClient] Subscribed to streams: {streams}")
        
        def _listen_loop():
            while self.is_connected:
                try:
                    data = json.loads(self.ws.recv())
                    callback(data)
                except Exception as e:
                    print(f"[CortexClient] Listener error: {e}")
                    break

        thread = threading.Thread(target=_listen_loop, daemon=True)
        thread.start()
        return True

    def close(self):
        """Cleanly close connection."""
        self.is_connected = False
        if self.ws:
            self.ws.close()
            print("[CortexClient] Closed connection.")