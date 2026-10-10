"""Consent-gated acquisition recording; bounded, paced replay; optional causal filtering."""
import json
from pathlib import Path
import time
from uuid import uuid4

from backend.data import finite_number

ROOT = Path(__file__).resolve().parents[1] / 'recordings'


class Acquisition:
    def __init__(self):
        self.file = None
        self.path = None
        self.loss = 0
        self.written = 0
        self.replay = None
        self.replay_next = None
        self.replay_start = None
        self.source_start = None
        self.filter = None
        self.filter_state = {}
        self.filter_last = None
        self.filter_rate = None
        self.replay_error = None
        self.replay_finished = False

    def start(self, metadata, consent):
        if not consent or self.file or self.replay:
            raise ValueError('Explicit consent and an idle recorder are required.')
        ROOT.mkdir(exist_ok=True)
        self.path = str(uuid4()) + '.jsonl'
        self.file = (ROOT / self.path).open('x', encoding='utf-8')
        self.loss = self.written = 0
        self.record({'kind': 'metadata', 'time': time.time(), 'consent': True, **metadata})

    def record(self, entry):
        if not self.file:
            return
        try:
            if self.written >= 512 * 1024 * 1024:
                raise OSError('Recording size limit reached.')
            line = json.dumps(entry, allow_nan=False) + '\n'
            self.file.write(line)
            self.written += len(line.encode())
        except (OSError, ValueError):
            self.loss += 1
            self.stop()

    def stop(self):
        if self.file:
            try:
                self.file.write(json.dumps({'kind': 'summary', 'time': time.time(), 'reported_loss': self.loss, 'bytes': self.written}) + '\n')
                self.file.flush()
                self.file.close()
            except OSError:
                self.loss += 1
            self.file = None

    def files(self):
        return sorted(f.name for f in ROOT.glob('*.jsonl'))[-100:]

    def start_replay(self, name):
        if self.file or self.replay or name not in self.files():
            raise ValueError('Stop recording/replay and choose an existing recording.')
        self.replay = (ROOT / name).open(encoding='utf-8')
        self.replay_error = None
        self.replay_finished = False
        self.replay_start = time.monotonic()
        self.source_start = None
        self.replay_next = None

    def stop_replay(self):
        if self.replay:
            self.replay.close()
        self.replay = self.replay_next = None

    def tick(self):
        batch = []
        for _ in range(256):
            if not self.replay or self.replay_finished:
                break
            if self.replay_next is None:
                line = self.replay.readline(1024 * 1024)
                if not line:
                    # Keep replay mode until operator exits, even at EOF.
                    self.replay_finished = True
                    break
                try:
                    entry = json.loads(line)
                    if not isinstance(entry, dict):
                        raise ValueError('Expected an object.')
                    if entry.get('kind') == 'sample':
                        sample = entry['sample']
                        if not finite_number(sample.get('time')) or not isinstance(sample.get('values'), dict) or not isinstance(entry.get('stream'), str):
                            raise ValueError('Malformed recorded sample.')
                        if not all(v is None or isinstance(v, (str, bool)) or finite_number(v) for v in sample['values'].values()):
                            raise ValueError('Malformed recorded values.')
                        if entry['stream'] == 'eeg' and (not all(finite_number(v) for v in sample['values'].values()) or not isinstance(sample.get('interpolated'), bool)):
                            raise ValueError('Malformed recorded EEG.')
                        json.dumps(sample, allow_nan=False)
                except (ValueError, TypeError, KeyError) as error:
                    self.replay_error = 'Malformed recording; Replay paused: ' + str(error)
                    self.replay_finished = True
                    break
                if entry.get('kind') != 'sample':
                    continue
                self.replay_next = entry
            entry = self.replay_next
            if self.source_start is None:
                self.source_start = entry['sample']['time']
            if entry['sample']['time'] - self.source_start > time.monotonic() - self.replay_start:
                break
            batch.append(entry)
            self.replay_next = None
        return batch

    def configure_filter(self, rate):
        if rate is None:
            self.filter = None
            self.filter_state.clear()
            return
        if not isinstance(rate, (int, float)) or not 90 < rate <= 2048:
            raise ValueError('Verified acquisition sample rate must exceed 90 Hz and be at most 2048 Hz.')
        from scipy.signal import butter
        self.filter = butter(4, [1, 40], btype='bandpass', fs=rate, output='sos')
        self.filter_rate = rate
        self.filter_state.clear()
        self.filter_last = None

    def filtered(self, sample):
        if self.filter is None:
            return None
        from scipy.signal import sosfilt, sosfilt_zi
        if self.filter_last is not None and sample['time'] - self.filter_last > 2 / self.filter_rate:
            self.filter_state.clear()
        self.filter_last = sample['time']
        values = {}
        for channel, value in sample['values'].items():
            zi = self.filter_state.get(channel)
            if zi is None:
                zi = sosfilt_zi(self.filter) * value
            out, self.filter_state[channel] = sosfilt(self.filter, [value], zi=zi)
            values[channel] = float(out[0])
        return {**sample, 'values': values}

    def snapshot(self):
        return {'active': self.file is not None, 'file': self.path, 'loss': self.loss,
                'bytes': self.written, 'replay': self.replay is not None, 'replay_error': self.replay_error, 'replay_finished': self.replay_finished,
                'filter': {'enabled': self.filter is not None, 'sample_rate': self.filter_rate,
                           'settings': 'Causal Butterworth order 4, 1–40 Hz; frequency-dependent delay'}}
