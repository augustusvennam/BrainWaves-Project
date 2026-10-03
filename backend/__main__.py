"""Run with python -m backend from the project root."""
import os
import uvicorn
from backend import config  # Loads .env before the server reads its port.

if __name__ == '__main__':
    config.Settings.from_env()
    port = int(os.getenv('BACKEND_PORT', '8000'))
    if not 1 <= port <= 65535:
        raise SystemExit('BACKEND_PORT must be between 1 and 65535.')
    uvicorn.run('backend.app:app', host=os.getenv('BACKEND_HOST', '127.0.0.1'), port=port)
