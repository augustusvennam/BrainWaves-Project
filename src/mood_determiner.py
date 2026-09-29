"""
Mood and Emotional State Classifier.
Processes real-time EEG performance metrics and frequency band powers
to categorize affective/cognitive state (Focused, Relaxed, Excited, Stressed, Neutral).

CORRECTIONS FROM REVIEW:
- 'met' stream at basic 0.1 Hz rate gives ~1-2 samples per 15s window — insufficient for reliable mood.
- Metrics need warm-up time before they stabilize.
- This is a HEURISTIC, not validated emotion detection. Label accordingly.
- Correct metric names: eng, exc, str, rel, int, lex (not just rel/foc)
"""
import time

class MoodDeterminer:
    def __init__(self, window_size=3, warmup_seconds=5.0):
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
        """Check if enough warmup time has passed for reliable metrics."""
        if self.start_time is None:
            return False
        return (time.time() - self.start_time) >= self.warmup_seconds

    def classify_from_metrics(self, metrics_data):
        """
        Classify mood from Emotiv 'met' performance metrics.
        metrics_data: dictionary with keys: eng, exc, str, rel, int, lex
        Values are scaled 0.0 to 1.0.
        
        NOTE: This is a HEURISTIC, not validated emotion detection.
        At basic 0.1 Hz license rate, you get ~1-2 samples per 15s window.
        Results should be presented as "likely state" not "detected emotion".
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