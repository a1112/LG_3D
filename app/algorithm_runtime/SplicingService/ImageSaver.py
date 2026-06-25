import threading
import multiprocessing
from multiprocessing import JoinableQueue as MulQueue
from queue import Queue as ThreadQueue

import numpy as np
from PIL import Image

import Globs
from Base.tools.compressed_storage import save_compressed_image, save_compressed_numpy
from Base.utils.Log import logger


class ImageSaver:
    """
    使用多进程执行
    修改为 继承
    """

    def __init__(self, managerQueue, loggerProcess):
        self.managerQueue = managerQueue
        self.num_processes = Globs.control.ImageSaverWorkNum
        self.type_ = Globs.control.ImageSaverThreadType
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
        self.queue.put((image, path, "pil"))

    def add_numpy(self, npy, path):
        self.queue.put((npy, path, "np"))

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
