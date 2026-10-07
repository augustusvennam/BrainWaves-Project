"""
Test script for Temi robot connectivity.

No mock mode — every method hits the temi-woz-android WebSocket app on Temi.
Set TEMI_DRY_RUN=1 to skip actual WebSocket calls (useful for CI / offline checks).
"""
import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.temi_controller import TemiController

DRY_RUN = os.environ.get("TEMI_DRY_RUN", "0") == "1"


def test_temi_connection():
    print("Testing Temi robot connection...")
    temi = TemiController(
        robot_ip="192.168.119.173",  # Change to your Temi's IP
        port=8175,
    )

    if DRY_RUN:
        print("[TEMI_DRY_RUN] Skipping real HTTP calls — validating controller wiring only.")

    def run(method, *args, **kwargs):
        if DRY_RUN:
            print(f"[TEMI_DRY_RUN] Would call {method.__name__}({args}, {kwargs})")
            return True
        return method(*args, **kwargs)

    print("Testing speech...")
    run(temi.speak, "Hello from BrainWaves Project test!")

    print("Testing movement...")
    run(temi.move_forward, 0.3)

    print("Testing turn...")
    run(temi.turn, 45)
    run(temi.turn, -45)

    print("Testing dance sequence...")
    run(temi.perform_dance)

    if not DRY_RUN:
        if temi.is_connected():
            print("✅ Temi robot reachable and responsive.")
        else:
            print("⚠️  Temi test completed — robot not reachable.")
    else:
        print("✅ Temi test completed (dry-run mode)")


if __name__ == "__main__":
    test_temi_connection()