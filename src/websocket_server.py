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
import ssl
import logging
import time
from datetime import datetime
from websockets.server import serve
from src.config import load_config
from src.mood_determiner import MoodDeterminer
from src.cortex_api_client import CortexClient

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

        # Initialize Cortex client
        self.cortex_client = CortexClient(
            client_id=self.emotiv_cfg['client_id'],
            client_secret=self.emotiv_cfg['client_secret'],
            url=self.emotiv_cfg['websocket_url']
        )

        # Initialize mood detector
        self.mood_detector = MoodDeterminer(window_size=self.mood_cfg['window_seconds'])

        # State
        self.current_metrics = {}
        self.current_command = None
        self.current_mood = 'Neutral'
        self.current_focus = 0.0

    async def connect(self):
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

        if not self.cortex_client.subscribe(['com', 'met', 'sys']):
            logger.error("Failed to subscribe to streams")
            self.cortex_client.close()
            return False

        # Register handlers
        self.cortex_client.register_handler('com', self._handle_command)
        self.cortex_client.register_handler('met', self._handle_metrics)
        self.cortex_client.register_handler('sys', self._handle_system)

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

                # Broadcast to all WebSocket clients
                self.broadcast({
                    'type': 'com',
                    'command': command,
                    'power': power,
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

                # Broadcast to all WebSocket clients
                self.broadcast({
                    'type': 'met',
                    'metrics': metrics,
                    'mood': self.current_mood,
                    'focus': self.current_focus,
                    'scores': result['scores'],
                    'raw': result['raw'],
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

                self.broadcast({
                    'type': 'sys',
                    'event': event,
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Error handling system event: {e}")

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
            'mood': self.current_mood,
            'focus': self.current_focus,
            'command': self.current_command,
            'metrics': self.current_metrics,
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

        # Connect to Cortex (blocking call)
        if not asyncio.run(self.connect()):
            logger.error("Failed to connect to Cortex. Exiting.")
            return

        logger.info("Cortex connected. Starting WebSocket server...")

        async def main():
            async with serve(self.handler, self.host, self.port):
                logger.info(f"WebSocket server running on ws://{self.host}:{self.port}")
                await asyncio.Future()  # run forever

        asyncio.run(main())

    def close(self):
        """Clean shutdown."""
        self.cortex_client.close()
        for client in list(self.clients):
            asyncio.create_task(client.close())
        logger.info("Server shutdown complete")


if __name__ == '__main__':
    server = EEGWebSocketServer()
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        server.close()