"""Bounded, thread-safe live state shared by Cortex and the web server."""
from collections import deque
from copy import deepcopy
import threading
import time

from backend.data import normalize_sample
from backend.participant import Participant
from backend.acquisition import Acquisition


class DashboardState:
    def __init__(self):
        self.lock = threading.RLock()
        self.revision = 0
        self.status = {'phase': 'starting', 'message': 'Starting local backend.'}
        self.connections = {name: {'status': 'unknown', 'message': 'Waiting for connection check.', 'checked_at': None}
                            for name in ('cortex', 'headset', 'temi')}
        self.headset = None
        self.session_id = None
        self.schemas = {}
        self.rejected = {}
        self.latest = {}
        self.eeg = deque(maxlen=256)
        self.arrivals = {}
        self.events = deque(maxlen=40)
        self.invalid_samples = 0
        self.participant = Participant()
        self.acquisition = Acquisition()
        self.sequence = 0
        self.eeg_sequence = 0
        self.epoch = 0
        self.metric_history = deque(maxlen=2048)
        self.filtered_eeg = deque(maxlen=256)
        self.counters = {'duplicates': 0, 'out_of_order': 0, 'buffer_overflow': 0, 'dropped_samples': 0, 'acquisition_gap_estimate': 0}
        self.profiles = {'items': [], 'current': {}, 'training': 'idle', 'training_action': None, 'training_event': None, 'neutral_accepted': False}
        self.commands = deque(maxlen=40)

    def event(self, message):
        with self.lock:
            event = {'time': time.time(), 'message': message}
            self.events.append(event)
            self.acquisition.record({'kind': 'event', **event})

    def participant_action(self, action):
        with self.lock:
            if self.acquisition.replay:
                raise ValueError('Exit Replay before operating a participant session.')
            self.participant.action(action)
            self.event('Participant: ' + action)
            if action in ('start', 'end', 'cancel'):
                self.clear_history()
                self.acquisition.stop()
                self.acquisition.configure_filter(None)
                self.commands.clear()

    def clear_history(self):
        self.latest.clear()
        self.eeg.clear()
        self.filtered_eeg.clear()
        self.metric_history.clear()
        self.arrivals.clear()
        self.epoch += 1

    def set_connection(self, name, status, message):
        with self.lock:
            self.connections[name] = {'status': status, 'message': message, 'checked_at': time.time()}
            self.revision += 1

    def set_status(self, phase, message):
        with self.lock:
            if self.status != {'phase': phase, 'message': message}:
                self.status = {'phase': phase, 'message': message}
                self.event(message)
                self.revision += 1

    def reset_session(self):
        with self.lock:
            replaying = self.acquisition.replay is not None
            if not replaying:
                self.clear_history()
            self.profiles.update(current={}, training='idle', training_action=None, training_event=None, neutral_accepted=False)
            if self.participant.phase != 'idle':
                self.participant = Participant()
                self.event('Participant cancelled because Cortex disconnected.')
            self.acquisition.stop()
            self.acquisition.configure_filter(None)
            self.headset = None
            self.session_id = None
            self.schemas.clear()
            self.rejected.clear()
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
            if self.acquisition.replay or not isinstance(payload, dict) or payload.get('sid') != self.session_id:
                return
            for stream, columns in self.schemas.items():
                if stream not in payload:
                    continue
                try:
                    sample = normalize_sample(stream, columns, payload)
                except (ValueError, TypeError, KeyError):
                    self.invalid_samples += 1
                    self.acquisition.loss += int(self.acquisition.file is not None)
                    self.revision += 1
                    continue
                previous = self.latest.get(stream)
                if previous and sample['time'] <= previous['time']:
                    key = 'duplicates' if sample['time'] == previous['time'] else 'out_of_order'
                    self.counters[key] += 1
                    self.acquisition.loss += int(self.acquisition.file is not None)
                    continue
                if stream == 'eeg' and previous:
                    rate = (self.headset or {}).get('settings', {}).get('eegRate')
                    if isinstance(rate, (int, float)) and rate > 0:
                        missed = max(0, round((sample['time'] - previous['time']) * rate) - 1)
                        self.counters['acquisition_gap_estimate'] += missed
                        if self.acquisition.file:
                            self.acquisition.loss += missed
                self.sequence += 1
                sample['sequence'] = self.sequence
                self.latest[stream] = sample
                if stream == 'sys':
                    self.profiles['training'] = str(sample['values'])
                    if sample['values'].get('event') == 'mentalCommand':
                        self.profiles['training_event'] = sample['values'].get('msg')
                    self.event('Training event: ' + self.profiles['training'])
                self.acquisition.record({'kind': 'sample', 'stream': stream, 'sample': sample,
                                         'quality': {s: self.latest.get(s) for s in ('dev', 'eq')},
                                         'raw_values': payload[stream], 'columns': columns})
                if stream == 'met':
                    self.metric_history.append(sample)
                    self.participant.receive(self.latest, self.connections['headset']['status'] == 'connected')
                arrivals = self.arrivals.setdefault(stream, deque(maxlen=2048))
                arrivals.append(time.monotonic())
                if stream == 'eeg':
                    self.eeg_sequence += 1
                    sample['eeg_sequence'] = self.eeg_sequence
                    if len(self.eeg) == self.eeg.maxlen:
                        self.counters['buffer_overflow'] += 1
                    self.eeg.append(sample)
                    filtered = self.acquisition.filtered(sample)
                    if filtered:
                        self.filtered_eeg.append(filtered)
                self.revision += 1

    def snapshot(self, after=None, eeg_after=None):
        with self.lock:
            if self.acquisition.replay:
                for entry in self.acquisition.tick():
                    stream, sample = entry['stream'], entry['sample']
                    self.sequence += 1
                    sample['sequence'] = self.sequence
                    self.latest[stream] = sample
                    if stream == 'eeg':
                        self.eeg_sequence += 1
                        sample['eeg_sequence'] = self.eeg_sequence
                        self.eeg.append(sample)
                    if stream == 'met':
                        self.metric_history.append(sample)
            now = time.monotonic()
            stream_status = {}
            for name in self.schemas:
                times = self.arrivals.get(name, [])
                recent = [t for t in times if now - t <= 2]
                rate = (len(recent) - 1) / (recent[-1] - recent[0]) if len(recent) > 1 and recent[-1] > recent[0] else None
                stream_status[name] = {
                    'age_seconds': max(now - times[-1], time.time() - self.latest[name]['time']) if times and name in self.latest else None,
                    'observed_hz': round(rate, 1) if rate is not None else None,
                }
            participant = self.participant.snapshot()
            if self.participant.phase != 'idle' and not self.acquisition.replay:
                reason = self.participant.gate(self.latest, self.connections['headset']['status'] == 'connected', time.time())
                if reason:
                    participant = {**participant, 'message': reason, 'estimate': {'state': 'Insufficient data', 'scores': {}, 'contributions': {}}}
            return deepcopy({
                'revision': self.revision, 'server_time': time.time(),
                'connections': self.connections,
                'status': self.status, 'headset': self.headset, 'session_id': self.session_id,
                'streams': stream_status, 'rejected_streams': self.rejected,
                'latest': self.latest,
                'eeg': [s for s in self.eeg if after is None or s['sequence'] > after],
                'filtered_eeg': [s for s in self.filtered_eeg if after is None or s['sequence'] > after],
                'metric_history': [s for s in self.metric_history if after is None or s['sequence'] > after], 'participant': participant,
                'recording': self.acquisition.snapshot(), 'profiles': self.profiles, 'commands': list(self.commands),
                'epoch': self.epoch, 'sequence': self.sequence, 'eeg_sequence': self.eeg_sequence, 'counters': self.counters,
                'feed_dropped': max(0, self.eeg[0]['eeg_sequence'] - eeg_after - 1) if eeg_after is not None and self.eeg else 0,
                'invalid_samples': self.invalid_samples, 'events': list(self.events),
            })
