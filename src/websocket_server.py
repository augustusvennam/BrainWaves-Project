"""Single acquisition owner: Cortex -> normalized events -> browser and optional Temi."""
import asyncio
import contextlib
import json
import logging
import time
from collections import deque

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed
from websockets import Headers, Request, Response
from websockets.utils import accept_key

from src.config import load_config, cortex_from_config
from src.mood_determiner import MoodDeterminer, valid_metrics, number
from src.temi_controller import TemiController

log = logging.getLogger(__name__)


def _accept_any_connection(connection, request):
    """Accept a WebSocket upgrade even if the Connection header lacks the
    'upgrade' token.

    Some browser/network stacks send 'Connection: keep-alive' on the upgrade
    request instead of 'Connection: Upgrade'. The Upgrade header, the
    Sec-WebSocket-Key, and the Sec-WebSocket-Accept handshake still fully
    authenticate the connection — only the overly-strict Connection token
    check is relaxed.

    Returns None to fall back to the library's default handshake, which
    enforces the RFC 6455 Connection header rules.
    """
    upgrade = request.headers.get('Upgrade', '')
    if upgrade.lower() != 'websocket':
        return None
    if 'Sec-WebSocket-Key' not in request.headers:
        return None
    key = request.headers['Sec-WebSocket-Key']
    return Response(101, 'Switching Protocols', Headers({
        'Connection': 'Upgrade',
        'Upgrade': 'websocket',
        'Sec-WebSocket-Accept': accept_key(key),
    }))


class EEGWebSocketServer:
    def __init__(self, config=None):
        self.config = config or load_config()
        self.clients = set()
        self.client = None
        self.detector = MoodDeterminer(**self.config['mood'])
        self.state = {'cortex_connected': False, 'temi_connected': False,
                      'metrics': {}, 'bands': {}, 'quality': {}, 'device': {},
                      'command': {}, 'command_history': [],
                      'last_sample_time': {}, 'assessment': self.detector.unknown('Waiting for Cortex'),
                      'status': 'Starting', 'streams': []}
        cfg = self.config['temi']
        self.temi = TemiController(cfg['robot_ip'], cfg['port'])
        self._last_spoken = None
        self._last_speech_time = float('-inf')
        self._speech_task = None
        self.queue = asyncio.Queue(maxsize=512)

    def _enqueue(self, stream, packet):
        if self.queue.full():
            self.queue.get_nowait()
        self.queue.put_nowait((stream, packet))

    def _connect(self, loop):
        self.client = cortex_from_config(self.config)
        if not self.client.connect():
            raise RuntimeError('Cannot reach Cortex with trusted TLS. Check Launcher and CORTEX_CA_FILE.')
        self.client.authenticate()
        self.client.query_headset()
        self.client.create_session(status='open')
        streams = self.config['emotiv']['streams']
        for stream in streams:
            self.client.register_handler(stream, lambda packet, s=stream:
                                         loop.call_soon_threadsafe(self._enqueue, s, packet))
        if not self.client.subscribe(streams):
            failed = ', '.join(item.get('streamName', '?') for item in self.client.subscription_failures)
            raise RuntimeError(f'Required streams unavailable: {failed or "missing subscription response"}')

    async def acquisition(self):
        loop = asyncio.get_running_loop()
        try:
            while True:
                try:
                    self.state['status'] = 'Connecting; approve the app in Launcher if prompted'
                    await asyncio.to_thread(self._connect, loop)
                    self.state.update(cortex_connected=True, status='Streaming',
                                      streams=list(self.client.columns))
                    while self.client.is_connected:
                        await asyncio.sleep(1)
                    raise RuntimeError('Cortex disconnected; retrying')
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    # Exception text contains no credential values or RPC parameters.
                    log.warning('%s', exc)
                    self.state.update(cortex_connected=False, status=str(exc), streams=[],
                                      metrics={}, bands={}, quality={}, device={},
                                      command={}, command_history=[], last_sample_time={})
                    self.detector = MoodDeterminer(**self.config['mood'])
                    self.state['assessment'] = self.detector.unknown('Cortex is unavailable')
                finally:
                    if self.client:
                        await asyncio.to_thread(self.client.close)
                    while not self.queue.empty():
                        self.queue.get_nowait()
                await asyncio.sleep(5)
        finally:
            self.state['cortex_connected'] = False

    async def process(self):
        while True:
            stream, packet = await self.queue.get()
            if not self.state['cortex_connected'] or packet.get('sid') != self.client.session_id:
                continue
            source_time = packet.get('time')
            max_age = 25 if stream == 'met' else 5
            if not number(source_time) or not -2 <= time.time() - source_time <= max_age:
                continue
            payload = packet[stream]
            self.state['last_sample_time'][stream] = packet.get('time')
            if stream == 'eq':
                self.state['quality'] = payload
                self.detector.update_quality(payload)
            elif stream == 'dev':
                self.state['device'] = payload
            elif stream == 'pow':
                self.state['bands'] = payload
            elif stream == 'com':
                # Mental command: {act: 'push'|'pull'|'lift'|'drop'|'neutral', pow: 0..1}
                self.state['command'] = payload
                self.state['command_history'].append((packet.get('time'), payload))
                if len(self.state['command_history']) > 200:
                    self.state['command_history'].pop(0)
            elif stream == 'met':
                active = valid_metrics(payload)
                # Keep inactive values explicitly null so charts cannot retain a false reading.
                self.state['metrics'] = {key: active.get(key) for key in
                                         ('eng', 'exc', 'str', 'rel', 'int', 'lex', 'attention', 'foc')}
                self.state['assessment'] = self.detector.classify_from_metrics(payload)
                await self.maybe_speak()
            await self.broadcast({'type': stream, 'data': {
                **(self.state['metrics'] if stream == 'met' else payload),
                'sample_time': packet.get('time'), 'assessment': self.state['assessment']}})

    async def maybe_speak(self):
        cfg, estimate = self.config['temi'], self.state['assessment']
        if not (cfg.get('enabled') and cfg.get('auto_speak') and estimate.get('stable')):
            return
        if self._speech_task and not self._speech_task.done():
            return
        mood = estimate['primary_mood']
        if mood == self._last_spoken or time.monotonic() - self._last_speech_time < cfg['cooldown_seconds']:
            return
        self._last_speech_time = time.monotonic()
        self._speech_task = asyncio.create_task(self._speak(mood))

    async def _speak(self, mood):
        try:
            await asyncio.to_thread(self.temi.speak, f'Your current readings suggest you may be {mood.lower()}.')
            self._last_spoken = mood
            self.state['temi_connected'] = True
        except Exception:
            self.state['temi_connected'] = False
            log.warning('Temi speech was not acknowledged')

    async def heartbeat(self):
        while True:
            invalid = self.detector.snapshot()
            if invalid:
                self.state['assessment'] = invalid
            if not self.state['cortex_connected']:
                self.state['assessment'] = self.detector.unknown('Cortex is unavailable')
            # Mark each metric null when the source is stale, even if browser is connected.
            if self.detector.last_metrics is None or time.monotonic() - self.detector.last_metrics > self.detector.stale_seconds:
                self.state['metrics'] = {}
            for stream, key in (('eq', 'quality'), ('dev', 'device'), ('pow', 'bands')):
                timestamp = self.state['last_sample_time'].get(stream)
                if timestamp is None or time.time() - timestamp > 5:
                    self.state[key] = {}
            # Mental commands update at 8 Hz; clear when the source goes stale.
            timestamp = self.state['last_sample_time'].get('com')
            if timestamp is None or time.time() - timestamp > 5:
                self.state['command'] = {}
            await self.broadcast({'type': 'state', 'data': self.state})
            await asyncio.sleep(1)

    async def temi_health(self):
        while True:
            if self.config['temi'].get('enabled'):
                self.state['temi_connected'] = await asyncio.to_thread(self.temi.is_connected)
            await asyncio.sleep(10)

    async def broadcast(self, message):
        encoded = json.dumps(message, allow_nan=False)
        for client in tuple(self.clients):
            try:
                await asyncio.wait_for(client.send(encoded), timeout=1)
            except (ConnectionClosed, TimeoutError):
                self.clients.discard(client)

    async def handler(self, ws):
        self.clients.add(ws)
        try:
            await ws.send(json.dumps({'type': 'state', 'data': self.state}, allow_nan=False))
            async for message in ws:
                try:
                    action = json.loads(message).get('type')
                    if action == 'reset_assessment':
                        self.detector = MoodDeterminer(**self.config['mood'])
                        self.state['assessment'] = self.detector.unknown('New participant; collecting samples')
                        self.state['metrics'] = {}
                        self.state['last_sample_time'].pop('met', None)
                        self._last_spoken = None
                    elif action == 'ping':
                        await ws.send(json.dumps({'type': 'pong', 'data': {}}))
                except (ValueError, AttributeError):
                    await ws.close(code=1003, reason='Expected a JSON object')
        except ConnectionClosed:
            pass
        finally:
            self.clients.discard(ws)

    async def run(self):
        cfg = self.config['server']
        async with serve(self.handler, cfg['host'], cfg['port'],
                         process_request=_accept_any_connection,
                         origins=['http://localhost:3000', 'http://127.0.0.1:3000',
                                  'http://localhost:4173', 'http://127.0.0.1:4173',
                                  'http://192.168.241.138:3000'], max_size=16384):
            log.info('Dashboard backend: ws://%s:%s', cfg['host'], cfg['port'])
            tasks = [asyncio.create_task(fn()) for fn in
                     (self.acquisition, self.process, self.heartbeat, self.temi_health)]
            try:
                await asyncio.gather(*tasks)
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                if self._speech_task:
                    with contextlib.suppress(Exception):
                        await self._speech_task


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    try:
        asyncio.run(EEGWebSocketServer().run())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
