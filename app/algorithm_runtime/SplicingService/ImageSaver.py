import os
import threading
import multiprocessing
from multiprocessing import JoinableQueue as MulQueue
from queue import Full, Queue as ThreadQueue

import numpy as np
from PIL import Image

import Globs
from Base.tools.compressed_storage import save_compressed_image, save_compressed_numpy
from Base.utils.Log import logger


DEFAULT_SAVE_QUEUE_PUT_TIMEOUT = 5.0


def _get_save_queue_put_timeout() -> float:
    raw_value = os.getenv("LG3D_IMAGE_SAVE_QUEUE_PUT_TIMEOUT", str(DEFAULT_SAVE_QUEUE_PUT_TIMEOUT))
    try:
        return max(float(raw_value), 0.1)
    except ValueError:
        logger.warning(
            "invalid LG3D_IMAGE_SAVE_QUEUE_PUT_TIMEOUT=%s, use %s",
            raw_value,
            DEFAULT_SAVE_QUEUE_PUT_TIMEOUT,
        )
        return DEFAULT_SAVE_QUEUE_PUT_TIMEOUT


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
        if self.type_ == "multiprocessing":
            self.queue = MulQueue(maxsize=Globs.control.ImageSaverQueueSize)
        else:
            self.queue = ThreadQueue(maxsize=Globs.control.ImageSaverQueueSize)
        self.processes = []
        self._initialize_processes()

    def _initialize_processes(self):
        for _ in range(self.num_processes):
            if self.type_ == "multiprocessing":
                process = multiprocessing.Process(target=self._save_images, args=(self.queue,))
            else:
                process = threading.Thread(target=self._save_images, args=(self.queue,))
            process.daemon = True
            self.processes.append(process)
            process.start()

    def add(self, obj, path):
        if isinstance(obj, np.ndarray):
            return self.add_numpy(obj, path)
        elif isinstance(obj, Image.Image):
            return self.add_image(obj, path)

    def add_image(self, image, path):
        return self._put_save_task((image, path, "pil"), path)

    def add_numpy(self, npy, path):
        return self._put_save_task((npy, path, "np"), path)

    def _put_save_task(self, task, path) -> bool:
        try:
            self.queue.put(task, timeout=self.queue_put_timeout)
            return True
        except Full:
            logger.error("image save queue full, drop save task path=%s", path)
        except Exception as e:
            logger.exception("image save queue put failed path=%s: %s", path, e)
        return False

    @staticmethod
    def _save_images(queue):
        while True:
            item = queue.get()
            if item is None:
                queue.task_done()
                break
            data, path, tp = item
            try:
                if tp == "pil":
                    save_compressed_image(data, path)
                elif tp == "np":
                    save_compressed_numpy(data, path)
            except Exception as e:
                logger.exception("Failed to save %s: %s", path, e)
            finally:
                queue.task_done()

    def join(self):
        # 阻塞直到所有任务完成
        self.queue.join()
        # 停止所有进程
        for _ in range(self.num_processes):
            self.queue.put(None)
        for process in self.processes:
            process.join()
