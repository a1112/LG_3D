import signal
import time

from .background import BackgroundRuntime


def run():
    runtime = BackgroundRuntime(enable=True)
    runtime.start()

    stop_event = False

    def _signal_handler(*_):
        nonlocal stop_event
        stop_event = True

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        while not stop_event:
            time.sleep(1)
    finally:
        runtime.stop()


if __name__ == "__main__":
    run()
