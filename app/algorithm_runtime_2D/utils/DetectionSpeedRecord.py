import os
import time
from datetime import datetime
from functools import wraps
from typing import Callable, TypeVar, Any

from algorithm_runtime_2D.utils.MultiprocessColorLogger import logger

T = TypeVar('T')


def _slow_log_seconds() -> float:
    try:
        return max(float(os.getenv("ALG_2D_SLOW_LOG_SECONDS", "3")), 0.0)
    except ValueError:
        return 3.0


SLOW_LOG_SECONDS = _slow_log_seconds()


class DetectionSpeedRecord:
    def __init__(self, coilId, surface):
        self.coilId = coilId
        self.surface = surface
        self.startTime = datetime.now()

    @staticmethod
    def timing_decorator(log_message: str = "") -> Callable[[Callable[..., T]], Callable[..., T]]:
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                start_time = time.perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    elapsed_time = time.perf_counter() - start_time
                    log_func = logger.warning if elapsed_time >= SLOW_LOG_SECONDS else logger.debug
                    log_func(
                        "timing_decorator %s: Function '%s' executed in %.4f seconds.",
                        log_message,
                        func.__name__,
                        elapsed_time,
                    )

            return wrapper

        return decorator
