"""
Helpers to start/stop the background runtime outside of FastAPI.
"""

import signal
import time
from typing import Callable

from runtime import runtime_controller
from utils.StdoutLog import Logger


def _make_signal_handler(stop_fn: Callable[[], None]):
    def _handler(signum, frame):
        stop_fn()
        raise SystemExit(0)

    return _handler


def run_runtime_forever(logger_name: str = "算法") -> None:
    """
    Start the background runtime and block the process until interrupted.
    Handles SIGINT/SIGTERM to stop gracefully.
    """
    Logger(logger_name)

    handler = _make_signal_handler(runtime_controller.stop)
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    runtime_controller.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handler(signal.SIGINT, None)
