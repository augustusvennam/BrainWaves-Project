"""
WebSocket server for streaming real-time EEG data to the frontend.

This server runs alongside brainbot_main.py and provides a WebSocket API
for the React dashboard to connect to. It bridges the Python Cortex client
with the browser-based frontend.

Usage:
    python src/websocket_server.py

The server will:
1. Connect to Cortex API (same as brainbot_main.py)
2. Subscribe to com, met, sys streams
3. Forward all data to connected WebSocket clients
4. Run on ws://localhost:8080 by default
"""
import asyncio
import json
import logging
from datetime import datetime
from websockets.server import serve
from src.config import load_config
from src.mood_determiner import MoodDeterminer
from src.cortex_api_client import CortexClient
from src.temi_controller import TemiController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EEGWebSocketServer:
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.clients = set()
        self.config = load_config()
        self.emotiv_cfg = self.config['emotiv']
        self.mood_cfg = self.config['mood']
        self.temi_cfg = self.config['temi']

        # Initialize Cortex client
        self.cortex_client = CortexClient(
            client_id=self.emotiv_cfg['client_id'],
            client_secret=self.emotiv_cfg['client_secret'],
            url=self.emotiv_cfg['websocket_url']
        )

        # Initialize mood detector
        self.mood_detector = MoodDeterminer(window_size=self.mood_cfg['window_seconds'])
        self.temi = TemiController(
            robot_ip=self.temi_cfg['robot_ip'],
            port=self.temi_cfg['port'],
        )

        # State
        self.current_metrics = {}
        self.current_command = None
        self.current_mood = 'Neutral'
        self.current_focus = 0.0
        self.current_eeg = []
        self.temi_connected = False
        self._event_loop = None

    def connect(self):
        """Connect to Cortex and start streaming."""
        logger.info("Connecting to Cortex...")

        if not self.cortex_client.connect():
            logger.error("Failed to connect to Cortex")
            return False

        if not self.cortex_client.authenticate():
            logger.error("Authentication failed")
            self.cortex_client.close()
            return False

        headset_id = self.cortex_client.query_headset()
        if not headset_id:
            logger.error("No headset detected")
            self.cortex_client.close()
            return False

        if not self.cortex_client.create_session():
            logger.error("Failed to create session")
            self.cortex_client.close()
            return False

        self.temi_connected = self.temi.is_connected()
        if self.temi_connected:
            logger.info("Temi WebSocket connected")
        else:
            logger.warning("Temi WebSocket is not reachable")

        # Register handlers
        self.cortex_client.register_handler('com', self._handle_command)
        self.cortex_client.register_handler('met', self._handle_metrics)
        self.cortex_client.register_handler('sys', self._handle_system)
        self.cortex_client.register_handler('eeg', self._handle_eeg)

        if not self.cortex_client.subscribe(['com', 'met', 'sys']):
            logger.error("Failed to subscribe to streams")
            self.cortex_client.close()
            return False
        try:
            if not self.cortex_client.subscribe(['eeg']):
                logger.warning("Raw EEG unavailable; showing derived metrics only")
        except Exception as error:
            logger.warning("Raw EEG unavailable (%s); showing derived metrics only", error)

        logger.info(f"Connected to headset: {headset_id}")
        return True

    def _handle_command(self, data):
        """Handle incoming mental command."""
        try:
            if 'com' in data:
                command = data['com'][0]
                power = data['com'][1]
                self.current_command = command
                logger.info(f"Command: {command} (power: {power:.2f})")

                self._schedule_broadcast({
                    'type': 'com',
                    'data': {
                        'command': command,
                        'power': power,
                    },
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Error handling command: {e}")

    def _handle_metrics(self, data):
        """Handle incoming performance metrics."""
        try:
            if 'met' in data:
                metrics = data['met']
                self.current_metrics = metrics

                # Classify mood
                result = self.mood_detector.classify_from_metrics(metrics)
                self.current_mood = result['primary_mood']
                self.current_focus = result['scores']['Focused']

                self._schedule_broadcast({
                    'type': 'met',
                    'data': {
                        **metrics,
                        'metrics': metrics,
                        'primary_mood': self.current_mood,
                        'focus_level': self.current_focus,
                        'scores': result['scores'],
                        'raw': result['raw'],
                    },
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Error handling metrics: {e}")

    def _handle_system(self, data):
        """Handle system events."""
        try:
            if 'sys' in data:
                event = data['sys']
                logger.info(f"System event: {event.get('type')}")

                self._schedule_broadcast({
                    'type': 'sys',
                    'data': {
                        'event': event,
                    },
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Error handling system event: {e}")

    def _handle_eeg(self, data):
        """Forward a compact raw EEG sample for BrainViz-style rendering."""
        sample = data.get('eeg')
        if not isinstance(sample, list):
            return
        numeric = [value for value in sample if isinstance(value, (int, float))]
        if not numeric:
            return
        self.current_eeg = numeric[-14:]
        self._schedule_broadcast({
            'type': 'eeg',
            'data': {'sample': self.current_eeg},
            'timestamp': datetime.now().isoformat(),
        })

    def _schedule_broadcast(self, message):
        """Schedule a broadcast from Cortex's background listener thread."""
        if self._event_loop is None or self._event_loop.is_closed():
            logger.warning("Dropping WebSocket message because the server loop is unavailable")
            return

        future = asyncio.run_coroutine_threadsafe(
            self.broadcast(message),
            self._event_loop,
        )
        future.add_done_callback(self._log_broadcast_failure)

    @staticmethod
    def _log_broadcast_failure(future):
        try:
            future.result()
        except Exception as error:
            logger.error(f"WebSocket broadcast failed: {error}")

    async def broadcast(self, message):
        """Send message to all connected WebSocket clients."""
        if not self.clients:
            return

        message_json = json.dumps(message)
        disconnected = set()

        for client in self.clients:
            try:
                await client.send(message_json)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.add(client)

        self.clients -= disconnected

    async def handler(self, websocket):
        """Handle new WebSocket connection."""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")

        # Send initial state
        await websocket.send(json.dumps({
            'type': 'state',
            'data': {
                **self.current_metrics,
                'metrics': self.current_metrics,
                'primary_mood': self.current_mood,
                'focus_level': self.current_focus,
                'command': self.current_command,
                'temi_connected': self.temi_connected,
                'eeg_available': bool(self.current_eeg),
            },
            'timestamp': datetime.now().isoformat()
        }))

        try:
            async for message in websocket:
                # Handle client messages (e.g., heartbeat)
                data = json.loads(message)
                if data.get('type') == 'ping':
                    await websocket.send(json.dumps({'type': 'pong'}))
        except Exception as e:
            logger.error(f"Client disconnected: {e}")
        finally:
            self.clients.discard(websocket)
            logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    def run(self):
        """Start the WebSocket server."""
        logger.info(f"Starting WebSocket server on ws://{self.host}:{self.port}")

        async def main():
            self._event_loop = asyncio.get_running_loop()

            # CortexClient uses blocking I/O and invokes handlers from its
            # listener thread, so keep it off the WebSocket event loop.
            if not await asyncio.to_thread(self.connect):
                logger.error("Failed to connect to Cortex. Exiting.")
                return

            logger.info("Cortex connected. Starting WebSocket server...")
            async with serve(self.handler, self.host, self.port):
                logger.info(f"WebSocket server running on ws://{self.host}:{self.port}")
                await asyncio.Future()  # run forever

            self._event_loop = None

        try:
            asyncio.run(main())
        finally:
            self._event_loop = None

    def close(self):
        """Clean shutdown."""
        self.cortex_client.close()
        logger.info("Server shutdown complete")


if __name__ == '__main__':
    server = EEGWebSocketServer()
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        server.close()