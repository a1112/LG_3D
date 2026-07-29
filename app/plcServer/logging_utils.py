import logging
import sys
from logging.handlers import QueueHandler, QueueListener, TimedRotatingFileHandler
from pathlib import Path
from queue import Full, Queue
from typing import Optional


class DroppingQueueHandler(QueueHandler):
    """Queue a log record without ever waiting on console or file I/O."""

    def __init__(self, log_queue: Queue):
        super().__init__(log_queue)
        self.dropped_records = 0

    def enqueue(self, record: logging.LogRecord) -> None:
        try:
            self.queue.put_nowait(record)
        except Full:
            self.dropped_records += 1


class _Sink:
    def __init__(self, handler: logging.Handler, queue_size: int) -> None:
        self.queue: Queue = Queue(maxsize=queue_size)
        self.queue_handler = DroppingQueueHandler(self.queue)
        self.listener = QueueListener(self.queue, handler, respect_handler_level=True)
        # QueueListener is a daemon thread. It is intentionally not joined at
        # shutdown because a frozen Windows console must not block termination.
        self.listener.start()


class LoggingRuntime:
    def __init__(self, sinks: list[_Sink]) -> None:
        self.sinks = sinks

    @property
    def dropped_records(self) -> int:
        return sum(sink.queue_handler.dropped_records for sink in self.sinks)


_runtime: Optional[LoggingRuntime] = None


def configure_nonblocking_logging(log_file: Path, queue_size: int = 2000) -> LoggingRuntime:
    """Make both application and Uvicorn output non-blocking and bounded."""
    global _runtime

    root_logger = logging.getLogger()
    if _runtime is not None:
        active_handlers = {sink.queue_handler for sink in _runtime.sinks}
        if active_handlers.issubset(root_logger.handlers):
            return _runtime

    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
        delay=True,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    size = max(int(queue_size), 1)
    sinks = [_Sink(file_handler, size), _Sink(console_handler, size)]
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    for sink in sinks:
        root_logger.addHandler(sink.queue_handler)
    root_logger.setLevel(logging.DEBUG)

    # Uvicorn's default StreamHandlers are synchronous. Propagating through
    # the bounded queues prevents a paused console from freezing the service.
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        service_logger = logging.getLogger(logger_name)
        for handler in service_logger.handlers[:]:
            service_logger.removeHandler(handler)
        service_logger.propagate = True

    _runtime = LoggingRuntime(sinks)
    return _runtime
