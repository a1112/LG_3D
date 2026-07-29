import logging
import threading
import time
from queue import Queue

from app.Base.utils.nonblocking_logging import DroppingQueueHandler


def test_dropping_queue_handler_never_waits_for_a_full_queue():
    log_queue = Queue(maxsize=1)
    handler = DroppingQueueHandler(log_queue)
    logger = logging.getLogger("test.nonblocking.full_queue")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    logger.info("first")
    started_at = time.monotonic()
    logger.error("must be dropped instead of blocking")

    assert time.monotonic() - started_at < 0.1
    assert handler.dropped_records == 1


def test_queue_handler_is_independent_from_a_blocked_sink():
    log_queue = Queue(maxsize=10)
    handler = DroppingQueueHandler(log_queue)
    logger = logging.getLogger("test.nonblocking.blocked_sink")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    sink_entered = threading.Event()
    release_sink = threading.Event()

    class BlockingSink(logging.Handler):
        def emit(self, record):
            sink_entered.set()
            release_sink.wait(timeout=2)

    sink = BlockingSink()

    def consume_one_record():
        record = log_queue.get(timeout=1)
        sink.handle(record)

    consumer = threading.Thread(target=consume_one_record)
    consumer.start()
    logger.info("blocks only the sink")
    assert sink_entered.wait(timeout=1)

    started_at = time.monotonic()
    logger.info("business thread remains responsive")
    assert time.monotonic() - started_at < 0.1

    release_sink.set()
    consumer.join(timeout=1)
    assert not consumer.is_alive()
