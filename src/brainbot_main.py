"""Compatibility entry point. Run one backend, not two acquisition processes."""
from src.websocket_server import main

if __name__ == '__main__':
    main()
