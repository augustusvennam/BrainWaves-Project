#!/bin/bash
# BrainWaves Project Environment Setup

echo "Setting up Python virtual environment..."
python -m venv venv
source venv/Scripts/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setup complete. To run scripts, use:"
echo "source venv/Scripts/activate"
