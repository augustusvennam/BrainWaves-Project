"""
Test script for Temi robot connectivity.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.temi_controller import TemiController
import time

def test_temi_connection():
    print("Testing Temi robot connection...")
    # Using mock mode by default - set mock=False when testing with real robot
    temi = TemiController(
        robot_ip="192.168.1.100",  # Change to your Temi's IP
        port=80,
        mock=True  # Set False for real hardware test
    )
    
    print("Testing speech...")
    temi.speak("Hello from BrainWaves Project test!")
    
    print("Testing movement...")
    temi.move_forward(0.3)
    
    print("Testing turn...")
    temi.turn(45)
    temi.turn(-45)
    
    print("Testing dance sequence...")
    temi.perform_dance()
    
    print("✅ Temi test completed (in mock mode)")

if __name__ == "__main__":
    test_temi_connection()
