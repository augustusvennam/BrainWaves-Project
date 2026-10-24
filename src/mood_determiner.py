"""Quality-gated, windowed demonstration heuristic; scores are not probabilities."""
from collections import deque
import math
import time


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def valid_metrics(metrics):
    result = {}
    for key in ('eng', 'exc', 'lex', 'str', 'rel', 'int', 'attention', 'foc'):
        value = metrics.get(key)
        active = metrics.get(f'{key}.isActive', True)
        if key == 'lex':
            active = metrics.get('exc.isActive', True)
        if active is True and number(value) and 0 <= value <= 1:
            result[key] = value
    return result


class MoodDeterminer:
    def __init__(self, window_seconds=60, min_samples=3, min_span_seconds=20,
                 stale_seconds=25, quality_stale_seconds=5, min_quality=70,
                 min_score_margin=0.08, stable_samples=2):
        self.window_seconds, self.min_samples = window_seconds, min_samples
        self.min_span_seconds, self.stale_seconds = min_span_seconds, stale_seconds
        self.quality_stale_seconds, self.min_quality = quality_stale_seconds, min_quality
        self.min_score_margin, self.stable_samples = min_score_margin, stable_samples
        self.history = deque()
        self.last_metrics = self.last_quality = None
        self.quality = None
        self.sample_rate_quality = None
        self.candidate, self.streak = None, 0

    def invalidate(self):
        self.history.clear()
        self.candidate, self.streak = None, 0

    def update_quality(self, data, now=None):
        now = time.monotonic() if now is None else now
        self.quality = data.get('overall')
        self.sample_rate_quality = data.get('sampleRateQuality')
        self.last_quality = now
        if not self._quality_ok(now):
            self.invalidate()

    def _quality_ok(self, now):
        return (self.last_quality is not None and now - self.last_quality <= self.quality_stale_seconds
                and number(self.quality) and self.quality >= self.min_quality
                and number(self.sample_rate_quality) and self.sample_rate_quality >= 0.9)

    @staticmethod
    def unknown(reason):
        return {'primary_mood': 'Insufficient data', 'reason': reason, 'scores': {},
                'focus_level': None, 'is_heuristic': True, 'stable': False}

    def snapshot(self, now=None):
        now = time.monotonic() if now is None else now
        if self.last_metrics is None or now - self.last_metrics > self.stale_seconds:
            self.invalidate()
            return self.unknown('Waiting for fresh performance metrics')
        if not self._quality_ok(now):
            self.invalidate()
            return self.unknown('EEG quality is low, unavailable, or stale')
        return None

    def classify_from_metrics(self, metrics, now=None):
        now = time.monotonic() if now is None else now
        self.snapshot(now)  # Clear previous history after a dropout.
        self.last_metrics = now
        if not self._quality_ok(now):
            self.invalidate()
            return self.unknown('Waiting for good EEG quality')
        values = valid_metrics(metrics)
        if not {'eng', 'exc', 'str', 'rel'}.issubset(values):
            self.invalidate()
            return self.unknown('Required metrics are inactive or missing')
        self.history.append((now, values))
        while self.history and now - self.history[0][0] > self.window_seconds:
            self.history.popleft()
        if len(self.history) < self.min_samples or now - self.history[0][0] < self.min_span_seconds:
            return self.unknown(f'Collecting valid samples ({len(self.history)}/{self.min_samples})')
        means = {key: sum(row[key] for _, row in self.history) / len(self.history)
                 for key in ('eng', 'exc', 'str', 'rel')}
        scores = {'Engaged': means['eng'], 'Excited': means['exc'],
                  'Stressed': means['str'], 'Relaxed': means['rel']}
        ranked = sorted(scores, key=scores.get, reverse=True)
        if scores[ranked[0]] < 0.55 or scores[ranked[0]] - scores[ranked[1]] < self.min_score_margin:
            self.candidate, self.streak = None, 0
            return self.unknown('No clearly dominant state')
        mood = ranked[0]
        self.streak = self.streak + 1 if self.candidate == mood else 1
        self.candidate = mood
        stable = self.streak >= self.stable_samples
        return {'primary_mood': mood if stable else 'Insufficient data',
                'reason': 'Stable estimate' if stable else 'Confirming estimate',
                'scores': scores, 'focus_level': values.get('attention', values.get('foc')),
                'is_heuristic': True, 'stable': stable}
