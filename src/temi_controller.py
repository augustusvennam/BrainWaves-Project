"""
Temi Robot Communication Layer.
Sends movement, speech, and animation commands to the Temi robot over local network.
Includes a Mock mode for development without hardware.
"""
import time
import requests

class TemiController:
    def __init__(self, robot_ip="192.168.1.100", port=80, mock=True):
        self.robot_ip = robot_ip
        self.port = port
        self.base_url = f"http://{robot_ip}:{port}/api"
        self.mock = mock

    def speak(self, text):
        """Make Temi speak a phrase via TTS."""
        if self.mock:
            print(f"[Temi (MOCK)] 🗣️ Speaking: \"{text}\"")
            return True
        try:
            resp = requests.post(f"{self.base_url}/tts", json={"text": text}, timeout=3)
            return resp.status_code == 200
        except Exception as e:
            print(f"[Temi] Speak failed: {e}")
            return False

    def move_forward(self, distance_meters=0.5):
        """Move forward by specified distance."""
        if self.mock:
            print(f"[Temi (MOCK)] 🤖 Moving forward {distance_meters}m")
            return True
        try:
            resp = requests.post(f"{self.base_url}/move", json={"distance": distance_meters}, timeout=3)
            return resp.status_code == 200
        except Exception as e:
            print(f"[Temi] Move failed: {e}")
            return False

    def turn(self, angle_degrees=90):
        """Turn by specified degrees (positive = right, negative = left)."""
        direction = "right" if angle_degrees > 0 else "left"
        if self.mock:
            print(f"[Temi (MOCK)] 🔄 Turning {direction} by {abs(angle_degrees)}°")
            return True
        try:
            resp = requests.post(f"{self.base_url}/turn", json={"angle": angle_degrees}, timeout=3)
            return resp.status_code == 200
        except Exception as e:
            print(f"[Temi] Turn failed: {e}")
            return False

    def perform_dance(self):
        """Execute a celebratory multi-step dance sequence."""
        print("[Temi] 💃 Starting BrainBot Dance Sequence!")
        self.speak("Awesome brainpower! Let's celebrate!")
        time.sleep(1.0)
        self.turn(45)
        time.sleep(0.5)
        self.turn(-90)
        time.sleep(0.5)
        self.turn(45)
        time.sleep(0.5)
        self.move_forward(0.3)
        self.speak("Mind control successful!")
        return True
