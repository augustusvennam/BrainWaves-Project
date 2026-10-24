"""Explicit speech-only hardware check; no movement commands."""
from src.config import load_config
from src.temi_controller import TemiController


def main():
    config = load_config()['temi']
    temi = TemiController(config['robot_ip'], config['port'])
    if not temi.is_connected():
        raise RuntimeError('Temi is not reachable or returned an unexpected greeting')
    if not temi.speak('Hello from the BrainWaves integration test.'):
        raise RuntimeError('Temi speech was not completed')
    print('PASS: Temi greeting and speech completion received')


if __name__ == '__main__':
    main()
