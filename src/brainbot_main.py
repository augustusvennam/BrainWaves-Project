"""
BrainBot Main Application.
Integrates Emotiv EEG processing with Temi robot control for a
brain-robot interaction demo: "Can you control a robot with your brain?"
"""

import json
import time
import yaml
import threading
import sys
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
            port=self.temi_cfg["port"]
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
        
        # Register callbacks via subscription
        self.cortex_client.subscribe(
            streams=['com', 'met', 'sys'],
            handlers={
                'com': self._on_mental_command,
                'met': self._on_performance_metrics,
                'sys': self._on_system_event
            }
        )

    # ----- Cortex Event Handlers -----
    def _on_mental_command(self, data):
        """Handle incoming mental command data stream."""
        try:
            if 'com' in data:
                command = data['com'][0]
                power = data['com'][1]
                self.last_mental_command = command
                self.last_command_time = time.time()
                print(f"[BrainBot] Mental command detected: {command} (power: {power:.2f})")
        except Exception as e:
            print(f"[BrainBot] Error processing com stream: {e}")

    def _on_performance_metrics(self, data):
        """Handle performance metrics (engagement, excitement, stress, relaxation, focus)."""
        try:
            if 'met' in data:
                metrics = data['met']
                # Classify mood using the real metrics
                result = self.mood_detector.classify_from_metrics(metrics)
                self.mood_assessment = result['primary_mood']
                self.focus_level = result['scores']['Focused']
                print(f"[BrainBot] Mood: {self.mood_assessment} (Focus: {self.focus_level:.2f})")
        except Exception as e:
            print(f"[BrainBot] Error processing met stream: {e}")

    def _on_system_event(self, data):
        """Handle system events (connection quality, battery, etc)."""
        try:
            if 'sys' in data:
                event = data['sys']
                if event.get('type') == 'connectionLost':
                    print("[BrainBot] WARNING: Headset connection lost!")
                    self.temi.speak("Warning: EEG connection lost. Please reconnect.")
                elif event.get('type') == 'batteryLevel' and event.get('level', 100) < 20:
                    print("[BrainBot] WARNING: Low battery detected!")
                    self.temi.speak("Warning: Headset battery is low. Please recharge.")
        except Exception as e:
            print(f"[BrainBot] Error processing sys stream: {e}")

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

    def wait_for_assessment(self):
        """Wait for a complete mood assessment from the mood detector."""
        self.mood_detector.start_session()
        while not self.mood_detector.is_ready():
            time.sleep(0.1)
        print("[BrainBot] Mood detector ready for assessment.")

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
        
        # Step 2: Wait for real mood assessment
        self.wait_for_assessment()
        print(f"[BrainBot] Detected mood: {self.mood_assessment} (Focus: {self.focus_level:.2f})")
        self.temi.speak(f"I detect you are feeling {self.mood_assessment.lower()} right now.")
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

        # 1. Connect to Cortex
        if not self.cortex_client.connect():
            print("[BrainBot] FATAL: Could not connect to Cortex service.")
            print("         Please ensure Cortex is running and accessible at wss://localhost:6868")
            sys.exit(1)

        # 2. Authenticate
        if not self.cortex_client.authenticate():
            print("[BrainBot] FATAL: Cortex authentication failed.")
            print("         Please configure valid credentials in config/settings.yaml")
            sys.exit(1)

        # 3. Find headset
        if not self.cortex_client.query_headset():
            print("[BrainBot] FATAL: No headset detected.")
            print("         Please connect an EPOC X headset and try again.")
            sys.exit(1)

        # 4. Create session
        if not self.cortex_client.create_session():
            print("[BrainBot] FATAL: Could not create recording session.")
            sys.exit(1)

        # 5. Subscribe to streams
        if not self.cortex_client.subscribe(['com', 'met', 'sys']):
            print("[BrainBot] FATAL: Could not subscribe to data streams.")
            sys.exit(1)

        # 6. Check Temi reachability
        if not self.temi.is_connected():
            print("[BrainBot] WARNING: Could not reach Temi robot.")
            print("         Robot actions will be simulated.")

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
