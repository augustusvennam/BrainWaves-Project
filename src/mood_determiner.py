"""
Mood and Emotional State Classifier.
Processes real-time EEG performance metrics and frequency band powers
to categorize affective/cognitive state (Focused, Relaxed, Excited, Stressed, Neutral).
"""

class MoodDeterminer:
    def __init__(self, window_size=3):
        self.window_size = window_size
        self.history = []

    def classify_from_metrics(self, metrics_data):
        """
        Classify mood from Emotiv 'met' performance metrics.
        metrics_data: dictionary or list containing engagement, excitement, stress, relaxation, focus.
        Typical 'met' stream structure: [eng, exc, str, rel, foc] (scaled 0.0 to 1.0)
        """
        if not metrics_data:
            return {"primary_mood": "Neutral", "confidence": 0.5, "scores": {}}

        # Fallback dictionary unpack if array provided
        if isinstance(metrics_data, list):
            # Map standard indices
            eng = metrics_data[0] if len(metrics_data) > 0 else 0.5
            exc = metrics_data[1] if len(metrics_data) > 1 else 0.5
            stress = metrics_data[2] if len(metrics_data) > 2 else 0.5
            rel = metrics_data[3] if len(metrics_data) > 3 else 0.5
            foc = metrics_data[4] if len(metrics_data) > 4 else 0.5
        elif isinstance(metrics_data, dict):
            eng = metrics_data.get("eng", 0.5)
            exc = metrics_data.get("exc", 0.5)
            stress = metrics_data.get("str", 0.5)
            rel = metrics_data.get("rel", 0.5)
            foc = metrics_data.get("foc", 0.5)
        else:
            return {"primary_mood": "Unknown", "confidence": 0.0, "scores": {}}

        scores = {
            "Focused": foc * 0.6 + eng * 0.4,
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
            "raw": {"engagement": eng, "excitement": exc, "stress": stress, "relaxation": rel, "focus": foc}
        }
