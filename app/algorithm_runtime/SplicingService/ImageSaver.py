import os
import threading
import multiprocessing
import time
from multiprocessing import JoinableQueue as MulQueue
from queue import Empty, Full, Queue as ThreadQueue

import numpy as np
from PIL import Image

import Globs
from Base.tools.compressed_storage import save_compressed_image, save_compressed_numpy
from Base.utils.Log import logger

DEFAULT_SAVE_QUEUE_PUT_TIMEOUT = 5.0
DEFAULT_SAVE_JOIN_TIMEOUT = 30.0
DEFAULT_SAVE_FLUSH_TIMEOUT = 120.0
MAX_FAILURE_RECORDS = 1000


def _get_save_queue_put_timeout() -> float:
    raw_value = os.getenv("LG3D_IMAGE_SAVE_QUEUE_PUT_TIMEOUT",
                          str(DEFAULT_SAVE_QUEUE_PUT_TIMEOUT))
    try:
        return max(float(raw_value), 0.1)
    except ValueError:
        logger.warning(
            "invalid LG3D_IMAGE_SAVE_QUEUE_PUT_TIMEOUT=%s, use %s",
            raw_value,
            DEFAULT_SAVE_QUEUE_PUT_TIMEOUT,
        )
        return DEFAULT_SAVE_QUEUE_PUT_TIMEOUT


def _get_save_join_timeout() -> float:
    raw_value = os.getenv("LG3D_IMAGE_SAVE_JOIN_TIMEOUT",
                          str(DEFAULT_SAVE_JOIN_TIMEOUT))
    try:
        return max(float(raw_value), 0.1)
    except ValueError:
        logger.warning(
            "invalid LG3D_IMAGE_SAVE_JOIN_TIMEOUT=%s, use %s",
            raw_value,
            DEFAULT_SAVE_JOIN_TIMEOUT,
        )
        return DEFAULT_SAVE_JOIN_TIMEOUT


def _get_save_flush_timeout() -> float:
    raw_value = os.getenv("LG3D_IMAGE_SAVE_FLUSH_TIMEOUT",
                          str(DEFAULT_SAVE_FLUSH_TIMEOUT))
    try:
        return max(float(raw_value), 0.1)
    except ValueError:
        logger.warning(
            "invalid LG3D_IMAGE_SAVE_FLUSH_TIMEOUT=%s, use %s",
            raw_value,
            DEFAULT_SAVE_FLUSH_TIMEOUT,
        )
        return DEFAULT_SAVE_FLUSH_TIMEOUT


class ImageSaver:
    """
    使用多进程执行
    修改为 继承
    """

    def __init__(self, managerQueue, loggerProcess):
        self.managerQueue = managerQueue
        self.num_processes = Globs.control.ImageSaverWorkNum
        self.type_ = Globs.control.ImageSaverThreadType
        self.queue_put_timeout = _get_save_queue_put_timeout()
        self.join_timeout = _get_save_join_timeout()
        self.flush_timeout = _get_save_flush_timeout()
        self._task_lock = threading.Lock()
        self._task_condition = threading.Condition(self._task_lock)
        self._flush_lock = threading.Lock()
        self._join_lock = threading.Lock()
        self._closed = False
        self._next_task_id = 0
        self._pending_task_ids = set()
        self._failed_task_ids = {}
        self._failed_task_overflow = 0
        self._ack_stop_event = threading.Event()
        self._ack_failure_event = (multiprocessing.Event()
                                   if self.type_ == "multiprocessing" else
                                   threading.Event())
        self._ack_error = ""
        queue_size = max(int(Globs.control.ImageSaverQueueSize), 1)
        ack_queue_size = max(queue_size, int(self.num_processes) * 2, 4)
        if self.type_ == "multiprocessing":
            self.queue = MulQueue(maxsize=queue_size)
            self.ack_queue = multiprocessing.Queue(maxsize=ack_queue_size)
        else:
            self.queue = ThreadQueue(maxsize=queue_size)
            self.ack_queue = ThreadQueue(maxsize=ack_queue_size)
        self._ack_thread = threading.Thread(
            target=self._collect_acknowledgements,
            name="ImageSaverAckCollector",
            daemon=True,
        )
        self._ack_thread.start()
        self.processes = []
        self._initialize_processes()

    def _initialize_processes(self):
        for _ in range(self.num_processes):
            if self.type_ == "multiprocessing":
                process = multiprocessing.Process(
                    target=self._save_images,
                    args=(self.queue, self.ack_queue,
                          self.queue_put_timeout, self._ack_failure_event),
                )
            else:
                process = threading.Thread(
                    target=self._save_images,
                    args=(self.queue, self.ack_queue,
                          self.queue_put_timeout, self._ack_failure_event),
                )
            process.daemon = True
            self.processes.append(process)
            process.start()

    def add(self, obj, path):
        if isinstance(obj, np.ndarray):
            return self.add_numpy(obj, path)
        elif isinstance(obj, Image.Image):
            return self.add_image(obj, path)

    def add_image(self, image, path):
        queued_image = image.copy()
        queued = self._put_save_task((queued_image, path, "pil"), path)
        if not queued:
            queued_image.close()
        return queued

    def add_numpy(self, npy, path):
        return self._put_save_task((npy, path, "np"), path)

    def _put_save_task(self, task, path) -> bool:
        if (self._ack_failure_event.is_set()
                or not self._ack_thread.is_alive()):
            logger.error(
                "image save acknowledgement collector unavailable, reject path=%s",
                path,
            )
            return False
        with self._task_condition:
            if self._closed:
                logger.error("image saver is closed, reject path=%s", path)
                return False
            task_id = self._next_task_id
            self._next_task_id += 1
            self._pending_task_ids.add(task_id)
        try:
            self.queue.put((task_id, *task), timeout=self.queue_put_timeout)
            return True
        except Full:
            logger.error("image save queue full, drop save task path=%s", path)
        except Exception as e:
            logger.exception("image save queue put failed path=%s: %s", path,
                             e)
        with self._task_condition:
            self._pending_task_ids.discard(task_id)
            self._task_condition.notify_all()
        return False

    @staticmethod
    def _save_images(queue, ack_queue, ack_timeout, ack_failure_event):
        while True:
            item = queue.get()
            if item is None:
                queue.task_done()
                break
            task_id, data, path, tp = item
            error = None
            try:
                if tp == "pil":
                    save_compressed_image(data, path)
                elif tp == "np":
                    save_compressed_numpy(data, path)
                else:
                    raise ValueError(f"unsupported image save type: {tp}")
            except Exception as e:
                error = f"{type(e).__name__}: {e}"
                logger.exception("Failed to save %s: %s", path, e)
            finally:
                if tp == "pil":
                    try:
                        data.close()
                    except Exception as e:
                        logger.warning("image close failed path=%s: %s", path,
                                       e)
                try:
                    ack_queue.put((task_id, error), timeout=ack_timeout)
                except Full:
                    ack_failure_event.set()
                    logger.error(
                        "image save acknowledgement queue full task=%s",
                        task_id,
                    )
                except Exception as e:
                    ack_failure_event.set()
                    logger.exception(
                        "image save acknowledgement failed task=%s: %s",
                        task_id, e)
                queue.task_done()
                # queue.get() blocks before assigning the next item; clear the
                # previous numpy/PIL payload now so an idle worker owns none.
                data = None
                item = None

    def _collect_acknowledgements(self):
        """Drain worker acknowledgements continuously so long runs stay bounded."""
        while not self._ack_stop_event.is_set():
            try:
                task_id, error = self.ack_queue.get(timeout=0.2)
            except Empty:
                continue
            except (EOFError, OSError, ValueError) as e:
                if not self._ack_stop_event.is_set():
                    self._ack_error = str(e)
                    logger.exception(
                        "image save acknowledgement collector failed: %s", e)
                break
            except Exception as e:
                self._ack_error = str(e)
                logger.exception(
                    "image save acknowledgement collector failed: %s", e)
                break
            with self._task_condition:
                self._pending_task_ids.discard(task_id)
                if error is not None:
                    if len(self._failed_task_ids) < MAX_FAILURE_RECORDS:
                        self._failed_task_ids[task_id] = error
                    else:
                        self._failed_task_overflow += 1
                self._task_condition.notify_all()

    def flush(self, timeout=None) -> bool:
        """Wait until every save queued before this call has completed."""
        if timeout is None:
            timeout = self.flush_timeout
        deadline = time.monotonic() + max(float(timeout), 0.1)
        with self._flush_lock:
            with self._task_condition:
                flush_before_task_id = self._next_task_id
                while True:
                    waiting_for = {
                        task_id for task_id in self._pending_task_ids
                        if task_id < flush_before_task_id
                    }
                    if not waiting_for:
                        break
                    if (self._ack_error
                            or self._ack_failure_event.is_set()
                            or not self._ack_thread.is_alive()):
                        logger.error(
                            "image save acknowledgement collector unavailable: pending=%s error=%s",
                            len(waiting_for),
                            self._ack_error or "worker acknowledgement failed",
                        )
                        return False
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        logger.error(
                            "image save flush timed out: pending=%s timeout=%ss",
                            len(waiting_for),
                            timeout,
                        )
                        return False
                    self._task_condition.wait(timeout=remaining)
                failures = [
                    (task_id, error)
                    for task_id, error in self._failed_task_ids.items()
                    if task_id < flush_before_task_id
                ]
                for task_id, _error in failures:
                    self._failed_task_ids.pop(task_id, None)
                if self._failed_task_overflow:
                    failures.append((
                        "overflow",
                        f"{self._failed_task_overflow} additional save failures",
                    ))
                    self._failed_task_overflow = 0
            if failures:
                logger.error("image save flush completed with failures: %s",
                             failures)
                return False
            return True

    def join(self):
        with self._join_lock:
            with self._task_lock:
                if self._closed:
                    return
                self._closed = True
            self._join()

    def _join(self):
        # 阻塞直到所有任务完成
        self.flush(timeout=self.flush_timeout)
        deadline = time.monotonic() + self.join_timeout
        sent_stop_count = 0
        while sent_stop_count < self.num_processes:
            timeout = max(
                min(self.queue_put_timeout, deadline - time.monotonic()), 0.1)
            try:
                self.queue.put(None, timeout=timeout)
                sent_stop_count += 1
            except Full:
                if time.monotonic() >= deadline:
                    logger.error(
                        "image save shutdown timed out while sending stop signals: sent=%s/%s",
                        sent_stop_count,
                        self.num_processes,
                    )
                    break
            except Exception as e:
                logger.exception(
                    "image save shutdown failed while sending stop signal: %s",
                    e)
                break
        # 停止所有进程
        for process in self.processes:
            process.join(timeout=self.join_timeout)
            if process.is_alive():
                logger.warning("image save worker did not exit within %ss: %s",
                               self.join_timeout, process)
                terminate = getattr(process, "terminate", None)
                if callable(terminate):
                    terminate()
                    process.join(timeout=2)
        if self.type_ == "multiprocessing":
            self._ack_stop_event.set()
            self._ack_thread.join(timeout=1)
            for queue in (self.queue, self.ack_queue):
                try:
                    queue.close()
                    queue.cancel_join_thread()
                except Exception as e:
                    logger.warning("image save queue close failed: %s", e)
        else:
            self._ack_stop_event.set()
            self._ack_thread.join(timeout=1)
