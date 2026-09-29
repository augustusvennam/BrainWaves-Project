"""
Emotiv Cortex API v2/v4 WebSocket Client Wrapper.
Handles authentication, session creation, mental command & performance metric subscriptions.
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
        self.callbacks = {}
        self.is_connected = False

    def connect(self):
        """Connect to local or remote Cortex WebSocket server."""
        print(f"[CortexClient] Connecting to {self.url}...")
        try:
            self.ws = websocket.create_connection(
                self.url,
                sslopt={"cert_reqs": ssl.CERT_NONE}
            )
            self.is_connected = True
            print("[CortexClient] Connected successfully.")
            return True
        except Exception as e:
            print(f"[CortexClient] Connection failed: {e}")
            self.is_connected = False
            return False

    def _send_request(self, method, params=None, req_id=1):
        """Send JSON-RPC request and return parsed response."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": req_id
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
        }, req_id=1)
        
        # 2. Authorize
        auth_resp = self._send_request("authorize", {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
            "debit": 1
        }, req_id=2)
        
        if "result" in auth_resp and "cortexToken" in auth_resp["result"]:
            self.auth_token = auth_resp["result"]["cortexToken"]
            print(f"[CortexClient] Authenticated successfully. Token acquired.")
            return True
        else:
            print(f"[CortexClient] Auth failed: {auth_resp}")
            return False

    def query_headset(self):
        """Scan for connected EPOC X or virtual headset."""
        resp = self._send_request("queryHeadsets", {}, req_id=3)
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
        }, req_id=4)
        if "result" in resp and "id" in resp["result"]:
            self.session_id = resp["result"]["id"]
            print(f"[CortexClient] Session created: {self.session_id}")
            return True
        print(f"[CortexClient] Failed to create session: {resp}")
        return False

    def subscribe(self, streams, callback):
        """Subscribe to data streams (e.g. ['com', 'met']) with live callback."""
        if not self.session_id or not self.auth_token:
            print("[CortexClient] Missing active session.")
            return False
            
        resp = self._send_request("subscribe", {
            "cortexToken": self.auth_token,
            "session": self.session_id,
            "streams": streams
        }, req_id=5)
        
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
