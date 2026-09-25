import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, TypeVar

from Base.utils.Log import logger

T = TypeVar("T")


class DetectionSpeedRecord:

    def __init__(self, coilId, surface):
        self.coilId = coilId
        self.surface = surface
        self.startTime = datetime.now()

    @staticmethod
    def timing_decorator(
        log_message: str = "",
        warning_seconds: float = 3.0,
        error_seconds: float = 60.0,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:

        def decorator(func: Callable[..., T]) -> Callable[..., T]:

            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                start_time = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed_time = time.perf_counter() - start_time
                log_func = logger.info
                if elapsed_time > warning_seconds:
                    log_func = logger.warning
                if elapsed_time > error_seconds:
                    log_func = logger.error
                log_func("timing %s: function=%s elapsed_s=%.1f", log_message,
                         func.__name__, elapsed_time)
                return result

            return wrapper

        return decorator
