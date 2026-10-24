"""Real hardware smoke test. Waits for actual samples; never claims a simulated pass."""
import argparse
import logging
import threading

from src.config import load_config, cortex_from_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=int, default=45)
    args = parser.parse_args()
    config = load_config()
    client = cortex_from_config(config)
    counts = {stream: 0 for stream in config['emotiv']['streams']}
    lock = threading.Lock()
    ready = threading.Event()

    def receive(stream, packet):
        with lock:
            counts[stream] += 1
            if all(counts.values()):
                ready.set()

    try:
        if not client.connect():
            raise RuntimeError('Cortex connection failed')
        client.authenticate()
        client.query_headset()
        client.create_session()
        for stream in counts:
            client.register_handler(stream, lambda packet, s=stream: receive(s, packet))
        if not client.subscribe(list(counts)):
            raise RuntimeError('At least one required stream was rejected')
        print('Subscribed columns:', client.columns)
        ready.wait(args.seconds)
        print('Actual packet counts:', counts)
        if not ready.is_set():
            raise RuntimeError('Not all requested streams delivered samples')
        print('PASS: all required streams delivered decoded samples. Check quality in the dashboard.')
    finally:
        client.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        main()
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(f'FAIL: {exc}') from None
