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
import queue
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
        # Per-stream handlers: {"com": handler, "met": handler, ...}
        # Registered via subscribe(); dispatched by the listener thread.
        self.message_handlers = {}
        self._req_counter = 0
        # The listener thread is the ONLY reader of the websocket. Request
        # responses are delivered through these per-id queues so _send_request
        # never calls ws.recv() itself (which would race with the listener).
        self._pending = {}
        self._req_lock = threading.Lock()
        self._stop_listening = threading.Event()
        self._listener_thread = None

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
            # Single reader thread — started here so _send_request never
            # races its own ws.recv() against this loop's ws.recv().
            self._stop_listening.clear()
            self._listener_thread = threading.Thread(
                target=self._listen_loop, daemon=True
            )
            self._listener_thread.start()
            return True
        except Exception as e:
            print(f"[CortexClient] Connection failed: {e}")
            self.is_connected = False
            return False

    def _send_request(self, method, params=None):
        """Send a JSON-RPC request and block on its response via the listener.

        Raises RuntimeError if Cortex does not reply within the timeout.
        """
        with self._req_lock:
            self._req_counter += 1
            req_id = self._req_counter
            q = queue.Queue()
            self._pending[req_id] = q

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": req_id
        }
        try:
            self.ws.send(json.dumps(payload))
        except Exception as e:
            with self._req_lock:
                self._pending.pop(req_id, None)
            raise RuntimeError(f"Cortex send failed: {e}") from e

        try:
            resp = q.get(timeout=10)
        except queue.Empty:
            with self._req_lock:
                self._pending.pop(req_id, None)
            raise RuntimeError("Cortex request timed out")
        finally:
            with self._req_lock:
                self._pending.pop(req_id, None)
        return resp

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

    def register_handler(self, stream, handler):
        """Register a callback for one stream type, e.g. register_handler('met', fn)."""
        self.message_handlers[stream] = handler

    def subscribe(self, streams, handlers=None):
        """Subscribe to data streams and register per-stream handlers.

        streams: list of stream names, e.g. ['com', 'met', 'fac', 'sys']
        handlers: optional dict of {stream_name: handler(payload)}.
            If omitted, messages are dispatched to self.message_handlers.

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

        # Merge caller-supplied handlers into the registry so the single
        # listener thread can route every stream to its owner.
        if handlers:
            for stream, handler in handlers.items():
                self.register_handler(stream, handler)

        try:
            resp = self._send_request("subscribe", {
                "cortexToken": self.auth_token,
                "session": self.session_id,
                "streams": streams
            })
        except RuntimeError as e:
            print(f"[CortexClient] Subscribe request failed: {e}")
            return False

        print(f"[CortexClient] Subscribed to streams: {streams}")
        return True

    def _listen_loop(self):
        """Single reader for the websocket.

        Routes each message: JSON-RPC responses (have an 'id') go to the
        waiting sender's queue; stream data (have a 'type' and 'sid') goes
        to the registered handler for that stream type.
        """
        while not self._stop_listening.is_set():
            try:
                raw_message = self.ws.recv()
                if not raw_message:
                    continue
                data = json.loads(raw_message)
            except json.JSONDecodeError:
                print("[CortexClient] Ignoring non-JSON WebSocket frame.")
                continue
            except Exception as e:
                print(f"[CortexClient] Listener error: {e}")
                break
            try:
                self._route(data)
            except Exception as e:
                print(f"[CortexClient] Routing error: {e}")

    def _route(self, data):
        """Dispatch one Cortex message to either the sender or a stream handler."""
        if not isinstance(data, dict):
            return

        # 1. JSON-RPC response to a pending request (has an 'id').
        if "id" in data:
            req_id = data["id"]
            with self._req_lock:
                q = self._pending.get(req_id)
            if q is not None:
                q.put(data)
            return

        # 2. Stream data — route to the handler for its stream type, but
        #    only if the message belongs to our session (sid match).
        stream_type = data.get("type")
        if stream_type is None:
            return
        if data.get("sid") != self.session_id:
            return
        handler = self.message_handlers.get(stream_type)
        if handler is None:
            return
        try:
            handler(data)
        except Exception as e:
            print(f"[CortexClient] Handler error for '{stream_type}': {e}")

    def close(self):
        """Cleanly close connection and stop the listener thread."""
        self._stop_listening.set()
        self.is_connected = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            print("[CortexClient] Closed connection.")