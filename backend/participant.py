"""Participant lifecycle and deliberately unvalidated baseline-relative heuristic."""
from collections import deque
import os
import math
import time
from uuid import uuid4

KEYS = ('rel', 'eng', 'exc', 'str')


class Participant:
    def __init__(self):
        self.id = None
        self.phase = 'idle'
        self.baseline = {}
        self.samples = deque(maxlen=2048)
        self.started = None
        self.candidate = None
        self.candidate_since = None
        self.estimate = {'state': 'Insufficient data', 'scores': {}, 'contributions': {}}
        self.message = 'Start a participant session.'
        self.config = {k: float(os.getenv('SESSION_' + k.upper(), str(v))) for k, v in {
            'baseline_seconds': 30, 'assessment_seconds': 20, 'minimum_samples': 10,
            'fresh_seconds': 15, 'smoothing_seconds': 15, 'persistence_seconds': 5,
            'quality_minimum': 60}.items()}
        if any(not math.isfinite(v) or not 0 < v <= 3600 for v in self.config.values()):
            raise ValueError('Session settings must be finite, positive and at most 3600.')
        if self.config['minimum_samples'] > 2048 or not self.config['minimum_samples'].is_integer():
            raise ValueError('SESSION_MINIMUM_SAMPLES must be an integer at most 2048.')
        if self.config['quality_minimum'] > 100:
            raise ValueError('SESSION_QUALITY_MINIMUM must be at most 100.')

    def action(self, action):
        transitions = {'baseline': ('ready', 'baseline'), 'assess': ('baseline_ready', 'assessment')}
        if action == 'start':
            if self.phase != 'idle':
                raise ValueError('End the current participant first.')
            self.id, self.phase = str(uuid4()), 'ready'
            self.message = 'Check contact and EEG quality, then collect baseline.'
        elif action in ('end', 'cancel'):
            self.__init__()
        elif action in transitions:
            before, after = transitions[action]
            if self.phase != before:
                raise ValueError('Invalid participant transition.')
            self.phase, self.started = after, time.time()
            self.samples.clear()
            self.candidate = self.candidate_since = None
            self.message = 'Collecting valid measurements; time alone does not complete this step.'
        elif action == 'confirm':
            if self.phase != 'review' or self.estimate['state'] not in ('Relaxed', 'Engaged', 'Excited', 'Stressed'):
                raise ValueError('No suitable estimate to confirm.')
            self.phase = 'confirmed'
        else:
            raise ValueError('Unknown participant action.')

    def gate(self, latest, connected, now):
        if not connected:
            return 'Headset disconnected; reconnect before collecting measurements.'
        for stream in ('met', 'dev', 'eq'):
            sample = latest.get(stream)
            if not sample or not 0 <= now - sample['time'] <= self.config['fresh_seconds']:
                return f'{stream} unavailable or stale; waiting for fresh measurements.'
        dev, eq = latest['dev']['values'], latest['eq']['values']
        if dev.get('OVERALL', -1) < self.config['quality_minimum'] or eq.get('overall', -1) < self.config['quality_minimum'] or eq.get('sampleRateQuality', -1) < .9:
            return 'Poor or unavailable contact/EEG quality; adjust headset.'
        if any(latest['met']['values'].get(k) is None for k in KEYS):
            return 'Insufficient active metrics: rel, eng, exc and str are required.'
        return None

    def receive(self, latest, connected, now=None):
        now = time.time() if now is None else now
        if self.phase not in ('baseline', 'assessment'):
            return
        reason = self.gate(latest, connected, now)
        if reason:
            self.message = reason
            self.candidate = self.candidate_since = None
            return
        sample = latest['met']
        if sample['time'] < self.started or (self.samples and sample['time'] <= self.samples[-1]['time']):
            return
        self.samples.append(sample)
        duration = self.samples[-1]['time'] - self.samples[0]['time']
        target = self.config['baseline_seconds' if self.phase == 'baseline' else 'assessment_seconds']
        self.message = f'{len(self.samples)} valid samples; {duration:.1f}/{target:g} seconds of valid data.'
        # Require coverage, not just two isolated endpoints.
        if len(self.samples) > 1 and sample['time'] - self.samples[-2]['time'] > self.config['fresh_seconds']:
            self.samples.clear()
            self.samples.append(sample)
            self.candidate = self.candidate_since = None
            return
        ready = duration >= target and len(self.samples) >= self.config['minimum_samples']
        if self.phase == 'baseline':
            if ready:
                self.baseline = {k: sum(s['values'][k] for s in self.samples) / len(self.samples) for k in KEYS}
                self.phase, self.message = 'baseline_ready', 'Baseline complete. Begin assessment when ready.'
            return
        window = [s for s in self.samples if sample['time'] - s['time'] <= self.config['smoothing_seconds']]
        delta = {k: sum(s['values'][k] for s in window) / len(window) - self.baseline[k] for k in KEYS}
        scores = {'Relaxed': delta['rel'] - delta['str'], 'Engaged': delta['eng'] - .5 * delta['str'],
                  'Excited': delta['exc'] - .5 * delta['str'], 'Stressed': delta['str'] - delta['rel']}
        ranked = sorted(scores, key=scores.get, reverse=True)
        winner = ranked[0] if scores[ranked[0]] >= .1 and scores[ranked[0]] - scores[ranked[1]] >= .05 else 'Unknown'
        if winner != self.candidate:
            self.candidate, self.candidate_since = winner, sample['time']
        persistent = sample['time'] - self.candidate_since >= self.config['persistence_seconds']
        self.estimate = {'state': winner if persistent else 'Insufficient data', 'scores': scores, 'contributions': delta}
        if ready and persistent:
            self.phase, self.message = 'review', 'Review the estimated state and contributing baseline-relative measurements.'

    def snapshot(self):
        return {'id': self.id, 'phase': self.phase, 'baseline': self.baseline, 'estimate': self.estimate,
                'message': self.message, 'valid_samples': len(self.samples), 'config': self.config}
