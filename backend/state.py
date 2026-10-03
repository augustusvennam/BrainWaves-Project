"""Bounded, thread-safe live state shared by Cortex and the web server."""
from collections import deque
from copy import deepcopy
import threading
import time

from backend.data import normalize_sample


class DashboardState:
    def __init__(self):
        self.lock = threading.RLock()
        self.revision = 0
        self.status = {'phase': 'starting', 'message': 'Starting local backend.'}
        self.headset = None
        self.session_id = None
        self.schemas = {}
        self.rejected = {}
        self.latest = {}
        self.eeg = deque(maxlen=256)
        self.arrivals = {}
        self.events = deque(maxlen=40)
        self.invalid_samples = 0

    def set_status(self, phase, message):
        with self.lock:
            if self.status != {'phase': phase, 'message': message}:
                self.status = {'phase': phase, 'message': message}
                self.events.append({'time': time.time(), 'message': message})
                self.revision += 1

    def reset_session(self):
        with self.lock:
            self.headset = None
            self.session_id = None
            self.schemas.clear()
            self.rejected.clear()
            self.latest.clear()
            self.eeg.clear()
            self.arrivals.clear()
            self.revision += 1

    def subscribe(self, result):
        with self.lock:
            for item in result.get('success', []):
                name = item['streamName']
                self.schemas[name] = item['cols']
            for item in result.get('failure', []):
                self.rejected[item['streamName']] = str(item.get('message', 'Subscription denied.'))
            self.revision += 1

    def receive(self, payload):
        with self.lock:
            if not isinstance(payload, dict) or payload.get('sid') != self.session_id:
                return
            for stream, columns in self.schemas.items():
                if stream not in payload:
                    continue
                try:
                    sample = normalize_sample(stream, columns, payload)
                except (ValueError, TypeError, KeyError):
                    self.invalid_samples += 1
                    self.revision += 1
                    continue
                self.latest[stream] = sample
                arrivals = self.arrivals.setdefault(stream, deque(maxlen=2048))
                arrivals.append(time.monotonic())
                if stream == 'eeg':
                    self.eeg.append(sample)
                self.revision += 1

    def snapshot(self):
        with self.lock:
            now = time.monotonic()
            stream_status = {}
            for name in self.schemas:
                times = self.arrivals.get(name, [])
                recent = [t for t in times if now - t <= 2]
                rate = (len(recent) - 1) / (recent[-1] - recent[0]) if len(recent) > 1 and recent[-1] > recent[0] else None
                stream_status[name] = {
                    'age_seconds': now - times[-1] if times else None,
                    'observed_hz': round(rate, 1) if rate is not None else None,
                }
            return deepcopy({
                'revision': self.revision, 'server_time': time.time(),
                'status': self.status, 'headset': self.headset, 'session_id': self.session_id,
                'streams': stream_status, 'rejected_streams': self.rejected,
                'latest': self.latest, 'eeg': list(self.eeg),
                'invalid_samples': self.invalid_samples, 'events': list(self.events),
            })
