"""
Temi Robot Communication Layer.

Real control path: this controller talks to a Temi robot over HTTP.
The Temi SDK is native Android — there is NO built-in HTTP/WebSocket API.
You must run an Android app on the robot that exposes an HTTP server
(this project's gateway). The real SDK methods are:
    goTo, skidJoy, turnBy, tiltBy, speak, stopMovement
No built-in "move 1 meter" or "dance" — build these from velocity primitives.

Safety: e-stop, speed limits, stop-on-signal-loss are required for
open-house crowds. All movement is gated by _check_safety().
"""

import time
import requests


class TemiController:
    """HTTP client for controlling a Temi mobile robot.

    Responsibilities:
      - Send TTS speech commands.
      - Move forward / turn / stop via the robot's HTTP gateway.
      - Enforce safety constraints (e-stop, signal-loss timeout).
    """

    def __init__(self, robot_ip="192.168.1.100", port=80,
                 max_speed_ms=0.3, enable_e_stop=True, stop_on_signal_loss=True,
                 signal_loss_timeout=3000):
        """Create a controller bound to a Temi robot's HTTP gateway.

        Args:
            robot_ip: Robot's IP address on the local network.
            port: HTTP port on the robot (default 80).
            max_speed_ms: Max movement speed in m/s (slow for open-house crowds).
            enable_e_stop: If True, block new movement while one is in flight.
            stop_on_signal_loss: If True, stop the robot when the controller
                hasn't been pinged within `signal_loss_timeout` ms.
            signal_loss_timeout: Milliseconds of silence before auto-stop.
        """
        self.robot_ip = robot_ip
        self.port = port
        self.base_url = f"http://{robot_ip}:{port}/api"

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

    def is_connected(self):
        """Lightweight reachability check against the robot gateway."""
        try:
            resp = requests.get(f"{self.base_url}/status", timeout=2)
            return resp.status_code == 200
        except Exception as e:
            print(f"[Temi] Status check failed: {e}")
            return False

    def speak(self, text):
        """Make Temi speak a phrase via TTS.
        Maps to real SDK: speak(text)
        """
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

        try:
            # Convert distance to time at max speed
            duration_s = distance_meters / self.max_speed_ms
            resp = requests.post(f"{self.base_url}/move", json={
                "distance": distance_meters,
                "max_speed": self.max_speed_ms
            }, timeout=3)
            if resp.status_code != 200:
                print(f"[Temi] Move rejected: HTTP {resp.status_code}")
                return False
            self._is_moving = True
            # Hold the e-stop line for the movement duration so a second
            # command cannot stack on top of an in-flight move.
            time.sleep(duration_s)
            self._is_moving = False
            return True
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
        try:
            resp = requests.post(f"{self.base_url}/turn", json={
                "angle": angle_degrees,
                "max_speed": self.max_speed_ms
            }, timeout=3)
            if resp.status_code != 200:
                print(f"[Temi] Turn rejected: HTTP {resp.status_code}")
                return False
            self._is_moving = True
            # Hold for the turn duration so the robot actually finishes turning.
            time.sleep(abs(angle_degrees) / 90.0 * 1.0)
            self._is_moving = False
            return True
        except Exception as e:
            print(f"[Temi] Turn failed: {e}")
            self._is_moving = False
            return False

    def stop_movement(self):
        """Emergency stop — maps to real SDK: stopMovement()"""
        self._is_moving = False
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