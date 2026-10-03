"""
Mood and Emotional State Classifier.

Reads Emotiv Cortex `met` (performance metrics) and maps the six scalar
signals to a small set of affective/cognitive labels:
    Focused, Relaxed, Excited, Stressed, Neutral.

IMPORTANT — this is a HEURISTIC, not validated emotion detection.
At the basic 0.1 Hz license rate you get ~1-2 samples per 15s window,
so results are best presented as "likely state", not "detected emotion".
"""

import time


class MoodDeterminer:
    """Heuristic classifier for Cortex `met` performance metrics.

    Responsibilities:
      - Track a rolling history of metric samples.
      - Enforce a warm-up period before classifying.
      - Convert raw metrics to a mood label + confidence score.
    """

    def __init__(self, window_size=3, warmup_seconds=5.0):
        """Create a classifier.

        Args:
            window_size: Number of metric samples to keep for smoothing.
            warmup_seconds: Seconds to wait before `is_ready()` returns True.
        """
        self.window_size = window_size
        self.warmup_seconds = warmup_seconds
        self.history = []
        self.start_time = None

    def start_session(self):
        """Begin a new assessment session. Call before reading metrics."""
        self.history = []
        self.start_time = time.time()
        print("[MoodDeterminer] Session started. Warmup period: {:.1f}s".format(self.warmup_seconds))

    def is_ready(self):
        """Return True once the warm-up period has elapsed since `start_session()`."""
        if self.start_time is None:
            return False
        return (time.time() - self.start_time) >= self.warmup_seconds

    def classify_from_metrics(self, metrics_data):
        """Classify mood from one Cortex `met` sample.

        Accepts either a dict (`{"eng": 0.5, ...}`) or a list
        (`[eng, exc, str, rel, int, lex]` — the standard Cortex order).

        Returns a dict with keys:
            primary_mood, confidence, scores, raw, is_heuristic, sample_rate_hz
        """
        if not metrics_data:
            return {"primary_mood": "Neutral", "confidence": 0.5, "scores": {}}

        # Handle both dict and list formats
        if isinstance(metrics_data, list):
            # Map standard indices: [eng, exc, str, rel, int, lex]
            eng = metrics_data[0] if len(metrics_data) > 0 else 0.5
            exc = metrics_data[1] if len(metrics_data) > 1 else 0.5
            stress = metrics_data[2] if len(metrics_data) > 2 else 0.5
            rel = metrics_data[3] if len(metrics_data) > 3 else 0.5
            interest = metrics_data[4] if len(metrics_data) > 4 else 0.5
            lex = metrics_data[5] if len(metrics_data) > 5 else 0.5
        elif isinstance(metrics_data, dict):
            eng = metrics_data.get("eng", 0.5)
            exc = metrics_data.get("exc", 0.5)
            stress = metrics_data.get("str", 0.5)
            rel = metrics_data.get("rel", 0.5)
            interest = metrics_data.get("int", 0.5)
            lex = metrics_data.get("lex", 0.5)
        else:
            return {"primary_mood": "Unknown", "confidence": 0.0, "scores": {}}

        # Heuristic classification — NOT validated emotion detection
        scores = {
            "Focused": eng * 0.5 + (exc + lex) * 0.25,
            "Relaxed": rel * 0.7 + (1.0 - stress) * 0.3,
            "Excited": exc * 0.6 + eng * 0.4,
            "Stressed": stress * 0.7 + (1.0 - rel) * 0.3,
            "Neutral": 0.45
        }

        # Determine dominant mood
        primary_mood = max(scores, key=scores.get)
        confidence = round(scores[primary_mood], 2)

        return {
            "primary_mood": primary_mood,
            "confidence": min(1.0, confidence),
            "scores": {k: round(v, 2) for k, v in scores.items()},
            "raw": {
                "engagement": eng,
                "excitement": exc,
                "stress": stress,
                "relaxation": rel,
                "interest": interest,
                "long_term_excitement": lex
            },
            "is_heuristic": True,
            "sample_rate_hz": 0.1  # Basic license rate
        }