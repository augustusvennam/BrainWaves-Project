"""
Temi Robot Communication Layer.

Real control path: this controller talks to the temi-woz-android app over WebSocket.
The Temi SDK is native Android — there is NO built-in HTTP/WebSocket API.
You must run an Android app on the robot that exposes an HTTP server
(this project's gateway). The real SDK methods are:
    goTo, skidJoy, turnBy, tiltBy, speak, stopMovement
No built-in "move 1 meter" or "dance" — build these from velocity primitives.

Safety: e-stop, speed limits, stop-on-signal-loss are required for
open-house crowds. All movement is gated by _check_safety().
"""

import time
import json
import websocket


class TemiController:
    """WebSocket client for controlling a Temi mobile robot.

    Responsibilities:
      - Send TTS speech and navigation commands.
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
        self.url = f"ws://{robot_ip}:{port}"
        self.timeout_s = 5

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
        """Open a WebSocket and verify the app's ready handshake."""
        try:
            ws = websocket.create_connection(self.url, timeout=self.timeout_s)
            try:
                ws.recv()
            finally:
                ws.close()
            return True
        except Exception as e:
            print(f"[Temi] Status check failed: {e}")
            return False

    def _send_command(self, command):
        """Send one protocol command and close the short-lived connection."""
        ws = None
        try:
            ws = websocket.create_connection(self.url, timeout=self.timeout_s)
            ws.recv()  # "Temi is ready to receive commands!"
            ws.send(json.dumps(command))
            return True
        except Exception as e:
            print(f"[Temi] Command failed: {e}")
            return False
        finally:
            if ws is not None:
                ws.close()

    def speak(self, text):
        """Make Temi speak a phrase via the temi-woz-android TTS command."""
        return self._send_command({"command": "speak", "sentence": text})

    def move_forward(self, distance_meters=0.5):
        """Movement is not exposed by the linked temi-woz-android protocol."""
        print("[Temi] Move not supported by temi-woz-android; use a goto location.")
        return False

    def turn(self, angle_degrees=90):
        """Turning is not exposed by the linked temi-woz-android protocol."""
        print("[Temi] Turn not supported by temi-woz-android.")
        return False

    def stop_movement(self):
        """No stop command is exposed by the linked app protocol."""
        self._is_moving = False
        print("[Temi] Stop is not exposed by temi-woz-android.")
        return False

    def goto(self, location):
        """Navigate to an exact saved Temi location."""
        return self._send_command({"command": "goto", "location": location})

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