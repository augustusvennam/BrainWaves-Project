"""
BrainBot Main Application.
Integrates Emotiv EEG processing with Temi robot control for a
brain-robot interaction demo: "Can you control a robot with your brain?"
"""

import json
import time
import yaml
import threading
from src.config import load_config
from src.cortex_api_client import CortexClient
from src.mood_determiner import MoodDeterminer
from src.temi_controller import TemiController

class BrainBot:
    def __init__(self):
        self.config = load_config()
        self.emotiv_cfg = self.config["emotiv"]
        self.eeg_cfg = self.config["eeg"]
        self.mood_cfg = self.config["mood"]
        self.temi_cfg = self.config["temi"]
        self.interact_cfg = self.config["interaction"]
        
        self.cortex_client = CortexClient(
            client_id=self.emotiv_cfg["client_id"],
            client_secret=self.emotiv_cfg["client_secret"],
            url=self.emotiv_cfg["websocket_url"]
        )
        
        self.mood_detector = MoodDeterminer(window_size=self.mood_cfg["window_seconds"])
        self.temi = TemiController(
            robot_ip=self.temi_cfg["robot_ip"],
            port=self.temi_cfg["port"],
            mock=True  # Set False when real Temi is available
        )
        
        # State tracking
        self.is_running = False
        self.last_mental_command = "neutral"
        self.last_command_time = 0
        self.mood_assessment = "Neutral"
        self.focus_level = 0.0
        
        # Mood classification thresholds
        self.focus_threshold_high = 0.7
        self.focus_threshold_med = 0.4
        
        # Register callbacks
        self.cortex_client.callbacks = {
            "com": self._on_mental_command,
            "met": self._on_performance_metrics,
            "sys": self._on_system_event,
            "eeg": self._on_eeg_data  # For debugging
        }

    # ----- Cortex Event Handlers -----
    def _on_mental_command(self, *args, **kwargs):
        """Handle incoming mental command data stream."""
        # Data format varies - inspect actual payload during live session
        # For now: placeholder for command detection
        pass

    def _on_performance_metrics(self, *args, **kwargs):
        """Handle performance metrics (engagement, excitement, stress, relaxation, focus)."""
        try:
            # The met stream typically sends [eng, exc, str, rel, foc] array or dict
            # For now we'll simulate - real implementation parses actual Cortex 'met' data
            # Example structure: {"met": [0.6, 0.3, 0.2, 0.7, 0.8]}
            pass
        except Exception as e:
            print(f"[BrainBot] Error processing met stream: {e}")

    def _on_system_event(self, *args, **kwargs):
        """Handle system events (connection quality, battery, etc)."""
        pass

    def _on_eeg_data(self, *args, **kwargs):
        """Handle raw EEG data - for advanced signal processing."""
        pass

    # ----- Core Logic -----
    def calibrate_user(self):
        """Guide user through initial mental command baseline training."""
        print("\n=== BRAINBOT CALIBRATION ===")
        print("Please focus and think of a clear mental command (e.g., PUSH) for 10 seconds...")
        self.temi.speak("Let's begin. Focus and think of pushing something forward.")
        time.sleep(self.interact_cfg["calibration_time"])
        print("Calibration complete. Ready for interaction!\n")
        self.temi.speak("Calibration complete. Ready to test your brainpower!")

    def assess_mood_from_simulated_data(self):
        """
        Simulate mood assessment when real EEG is not available.
        Replace with real met-stream processing once headset is connected.
        """
        import random
        # Simulate varied mood states for demo
        mood_options = ["Focused", "Relaxed", "Excited", "Stressed", "Neutral"]
        weights = [0.2, 0.3, 0.2, 0.1, 0.2]  # Biased toward relaxed/neutral for demo
        mood = random.choices(mood_options, weights=weights)[0]
        confidence = round(random.uniform(0.6, 0.9), 2)
        
        # Map to focus level for robot control
        mood_to_focus = {
            "Focused": 0.8 + random.uniform(0, 0.2),
            "Excited": 0.6 + random.uniform(0, 0.2),
            "Relaxed": 0.3 + random.uniform(0, 0.2),
            "Stressed": 0.4 + random.uniform(0, 0.2),
            "Neutral": 0.5 + random.uniform(-0.1, 0.1)
        }
        
        self.mood_assessment = mood
        self.focus_level = max(0.0, min(1.0, mood_to_focus[mood]))
        return mood, confidence

    def determine_robot_action(self):
        """
        Decide what action Temi should take based on current mental state.
        Returns: action_name, action_params
        """
        # If we have a clear mental command trigger
        if self.last_mental_command in ["push", "lift"] and self.focus_level > 0.6:
            # Strong focus + push/lift = celebration dance
            return "celebration_dance", {}
        
        # Otherwise, use mood/focus level for graduated response
        if self.focus_level >= self.focus_threshold_high:
            # High focus: move forward
            return "move_forward", {"distance": 0.8}
        elif self.focus_level >= self.focus_threshold_med:
            # Medium focus: turn in place
            return "turn", {"angle": 30}  # Gentle right turn
        else:
            # Low focus: attract attention
            return "attract_attention", {}

    def execute_action(self, action_name, params=None):
        """Execute the determined action on the Temi robot."""
        params = params or {}
        print(f"[BrainBot] Executing action: {action_name} with {params}")
        
        if action_name == "move_forward":
            self.temi.move_forward(params.get("distance", 0.5))
        elif action_name == "turn":
            self.temi.turn(params.get("angle", 45))
        elif action_name == "celebration_dance":
            self.temi.perform_dance()
        elif action_name == "attract_attention":
            self.temi.speak("I sense you might need more focus. Let's try again!")
            self.temi.turn(-20)  # Left
            time.sleep(0.5)
            self.temi.turn(40)   # Right
        elif action_name == "speak_only":
            self.temi.speak(params.get("text", "Hello from BrainBot!"))

    def run_demo_cycle(self):
        """Execute one complete demo interaction cycle."""
        print("\n--- Starting BrainBot Demo Cycle ---")
        
        # Step 1: Calibration
        self.calibrate_user()
        
        # Step 2: Mood assessment
        mood, confidence = self.assess_mood_from_simulated_data()
        print(f"[BrainBot] Detected mood: {mood} (confidence: {confidence})")
        self.temi.speak(f"I detect you are feeling {mood.lower()} right now.")
        time.sleep(2.0)
        
        # Step 3: Mental command & focus assessment (simulated)
        print("[BrainBot] Assessing mental focus and command readiness...")
        time.sleep(2.0)
        
        # Step 4: Determine and execute action
        action_name, params = self.determine_robot_action()
        self.execute_action(action_name, params)
        
        # Step 5: Feedback and reset
        time.sleep(3.0)
        print("[BrainBot] Demo cycle complete. Ready for next visitor.\n")
        self.temi.speak("Thank you for trying BrainBot!")
        time.sleep(1.0)

    def start(self):
        """Start the BrainBot application."""
        print("\n" + "="*50)
        print("BRAINBOT: Brain-Controlled Robotics Demo")
        print("="*50)
        print("\nInitializing systems...")
        
        # Test Cortex connection (will fail without credentials/device - that's OK for now)
        if not self.cortex_client.connect():
            print("[BrainBot] Warning: Could not connect to Cortex service.")
            print("         Running in SIMULATION MODE - ready for when headset is available.")
        
        # Attempt authentication (will fail without valid credentials)
        try:
            if not self.cortex_client.authenticate():
                print("[BrainBot] Warning: Cortex authentication failed.")
                print("         Please configure valid credentials in config/settings.yaml")
        except Exception as e:
            print(f"[BrainBot] Auth error (expected without credentials): {e}")
        
        print("\nStarting demo loop. Press Ctrl+C to exit.\n")
        self.is_running = True
        
        try:
            while self.is_running:
                self.run_demo_cycle()
                # Brief pause between visitors
                time.sleep(5.0)
        except KeyboardInterrupt:
            print("\n\nBrainBot shutting down gracefully...")
        finally:
            self.stop()

    def stop(self):
        """Clean shutdown."""
        self.is_running = False
        if hasattr(self.cortex_client, 'ws') and self.cortex_client.ws:
            self.cortex_client.ws.close()
        print("[BrainBot] Shutdown complete.")

def main():
    app = BrainBot()
    app.start()

if __name__ == "__main__":
    main()
