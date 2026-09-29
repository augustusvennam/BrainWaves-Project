"""
Temi Robot Communication Layer.

CRITICAL CORRECTIONS FROM REVIEW:
- Temi SDK is native Android — there is NO built-in HTTP/WebSocket API.
- You must build an Android app on the robot that exposes an HTTP/WebSocket server.
- Real SDK methods: goTo, skidJoy, turnBy, tiltBy, speak, stopMovement
- No built-in "move 1 meter" or "dance" — build these from velocity primitives.
- Safety: e-stop, speed limits, stop-on-signal-loss required for open house crowds.
"""
import time
import requests

class TemiController:
    def __init__(self, robot_ip="192.168.1.100", port=80, mock=True,
                 max_speed_ms=0.3, enable_e_stop=True, stop_on_signal_loss=True,
                 signal_loss_timeout=3000):
        self.robot_ip = robot_ip
        self.port = port
        self.base_url = f"http://{robot_ip}:{port}/api"
        self.mock = mock
        
        # Safety settings
        self.max_speed_ms = max_speed_ms  # m/s — slow for open house crowds
        self.enable_e_stop = enable_e_stop
        self.stop_on_signal_loss = stop_on_signal_loss
        self.signal_loss_timeout = signal_loss_timeout  # ms
        self.last_signal_time = time.time()
        self._is_moving = False

    def _check_safety(self):
        """Safety check before any movement. Returns True if safe to proceed."""
        if self.enable_e_stop and self._is_moving:
            print("[Temi Safety] E-STOP active — cannot execute new movement.")
            return False
        if self.stop_on_signal_loss:
            elapsed_ms = (time.time() - self.last_signal_time) * 1000
            if elapsed_ms > self.signal_loss_timeout:
                print(f"[Temi Safety] Signal lost for {elapsed_ms:.0f}ms — stopping.")
                self.stop_movement()
                return False
        return True

    def _update_signal(self):
        """Called by external watchdog to confirm controller is alive."""
        self.last_signal_time = time.time()

    def speak(self, text):
        """Make Temi speak a phrase via TTS.
        Maps to real SDK: speak(text)
        """
        if self.mock:
            print(f"[Temi (MOCK)] 🗣️ Speaking: \"{text}\"")
            return True
        try:
            resp = requests.post(f"{self.base_url}/speak", json={"text": text}, timeout=3)
            return resp.status_code == 200
        except Exception as e:
            print(f"[Temi] Speak failed: {e}")
            return False

    def move_forward(self, distance_meters=0.5):
        """Move forward by specified distance.
        Built from skidJoy primitives — NOT a native SDK method.
        """
        if not self._check_safety():
            return False
        
        if self.mock:
            print(f"[Temi (MOCK)] 🤖 Moving forward {distance_meters}m")
            self._is_moving = True
            time.sleep(distance_meters / self.max_speed_ms)
            self._is_moving = False
            return True
        
        try:
            # Convert distance to time at max speed
            duration_s = distance_meters / self.max_speed_ms
            resp = requests.post(f"{self.base_url}/move", json={
                "distance": distance_meters,
                "max_speed": self.max_speed_ms
            }, timeout=3)
            self._is_moving = True
            return resp.status_code == 200
        except Exception as e:
            print(f"[Temi] Move failed: {e}")
            self._is_moving = False
            return False

    def turn(self, angle_degrees=90):
        """Turn by specified degrees (positive = right, negative = left).
        Built from turnBy primitives — NOT a native SDK method.
        """
        if not self._check_safety():
            return False
        
        direction = "right" if angle_degrees > 0 else "left"
        if self.mock:
            print(f"[Temi (MOCK)] 🔄 Turning {direction} by {abs(angle_degrees)}°")
            return True
        
        try:
            resp = requests.post(f"{self.base_url}/turn", json={
                "angle": angle_degrees,
                "max_speed": self.max_speed_ms
            }, timeout=3)
            return resp.status_code == 200
        except Exception as e:
            print(f"[Temi] Turn failed: {e}")
            return False

    def stop_movement(self):
        """Emergency stop — maps to real SDK: stopMovement()"""
        self._is_moving = False
        if self.mock:
            print("[Temi (MOCK)] 🛑 STOP")
            return True
        try:
            resp = requests.post(f"{self.base_url}/stop", timeout=2)
            return resp.status_code == 200
        except Exception as e:
            print(f"[Temi] Stop failed: {e}")
            return False

    def perform_dance(self):
        """Execute a celebratory multi-step dance sequence.
        Built from primitives: speak → turn → move → speak.
        """
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