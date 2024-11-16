import time
from datetime import datetime
from typing import Callable, TypeVar, Any
from utils.Log import logger
T = TypeVar('T')

class DetectionSpeedRecord :
    def __init__(self, coilId,surface):
        self.coilId = coilId
        self.surface = surface
        self.startTime = datetime.now()

    @staticmethod
    def timing_decorator(log_message: str="") -> Callable[[Callable[..., T]], Callable[..., T]]:
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args: Any, **kwargs: Any) -> T:
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                elapsed_time = end_time - start_time
                logger.info(f"timing_decorator {log_message}: Function '{func.__name__}' executed in {elapsed_time:.4f} seconds.")
                return result

            return wrapper

        return decorator
