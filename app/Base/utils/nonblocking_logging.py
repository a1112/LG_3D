import logging
import os
import sys
from logging.handlers import QueueHandler, QueueListener, TimedRotatingFileHandler
from pathlib import Path
from queue import Full, Queue
from typing import Iterable, Optional


DEFAULT_LOG_QUEUE_MAXSIZE = 5000


class DroppingQueueHandler(QueueHandler):
    """Never let a slow log destination block an application thread."""

    def __init__(self, log_queue: Queue):
        super().__init__(log_queue)
        self.dropped_records = 0

    def enqueue(self, record: logging.LogRecord) -> None:
        try:
            self.queue.put_nowait(record)
        except Full:
            self.dropped_records += 1


class ExcludeLoggerFilter(logging.Filter):
    def __init__(self, logger_names: Iterable[str]):
        super().__init__()
        self.logger_names = tuple(logger_names)

    def filter(self, record: logging.LogRecord) -> bool:
        return not any(
            record.name == name or record.name.startswith(f"{name}.")
            for name in self.logger_names
        )


class _AsyncLogSink:
    def __init__(self, handler: logging.Handler, queue_maxsize: int):
        self.queue = Queue(maxsize=queue_maxsize)
        self.queue_handler = DroppingQueueHandler(self.queue)
        self.queue_handler.setLevel(handler.level)
        self.listener = QueueListener(
            self.queue,
            handler,
            respect_handler_level=True,
        )
        # QueueListener uses a daemon thread. Do not stop/join it at process
        # shutdown: a frozen Windows console could otherwise block shutdown.
        self.listener.start()


class NonBlockingLoggingRuntime:
    def __init__(self, sinks: list[_AsyncLogSink]):
        self.sinks = sinks

    @property
    def dropped_records(self) -> int:
        return sum(sink.queue_handler.dropped_records for sink in self.sinks)


_runtime: Optional[NonBlockingLoggingRuntime] = None


def _queue_maxsize(value: Optional[int]) -> int:
    if value is not None:
        return max(int(value), 1)
    raw_value = os.getenv("LG3D_LOG_QUEUE_MAXSIZE", str(DEFAULT_LOG_QUEUE_MAXSIZE))
    try:
        return max(int(raw_value), 1)
    except ValueError:
        return DEFAULT_LOG_QUEUE_MAXSIZE


def configure_nonblocking_logging(
    log_file: Path,
    *,
    root_level: int = logging.DEBUG,
    file_level: int = logging.DEBUG,
    console_level: int = logging.INFO,
    queue_maxsize: Optional[int] = None,
    console_excluded_loggers: Iterable[str] = ("uvicorn.access",),
) -> NonBlockingLoggingRuntime:
    """Route root logs through bounded queues so I/O cannot stall the service."""
    global _runtime

    root_logger = logging.getLogger()
    if _runtime is not None:
        runtime_handlers = {
            sink.queue_handler
            for sink in _runtime.sinks
        }
        if runtime_handlers and runtime_handlers.issubset(root_logger.handlers):
            return _runtime

    maxsize = _queue_maxsize(queue_maxsize)
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
        delay=True,
    )
    file_handler.suffix = "%Y-%m-%d.log"
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    excluded = tuple(console_excluded_loggers)
    if excluded:
        console_handler.addFilter(ExcludeLoggerFilter(excluded))

    sinks = [
        _AsyncLogSink(file_handler, maxsize),
        _AsyncLogSink(console_handler, maxsize),
    ]
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    for sink in sinks:
        root_logger.addHandler(sink.queue_handler)
    root_logger.setLevel(root_level)

    # Uvicorn otherwise installs direct StreamHandlers which reintroduce the
    # same console back-pressure problem.
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        service_logger = logging.getLogger(logger_name)
        for handler in service_logger.handlers[:]:
            service_logger.removeHandler(handler)
        service_logger.propagate = True

    _runtime = NonBlockingLoggingRuntime(sinks)
    return _runtime
