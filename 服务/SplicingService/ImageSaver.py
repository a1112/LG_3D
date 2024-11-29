# import threading
# from queue import Queue
#
# import numpy as np
#
#
# class ImageSaver:
#     """
#     使用多线程执行
#     """
#     def __init__(self, num_threads=30):
#         self.num_threads = num_threads
#         self.queue = Queue()
#         self.threads = []
#         self._initialize_threads()
#
#     def _initialize_threads(self):
#         for _ in range(self.num_threads):
#             thread = threading.Thread(target=self._save_images)
#             thread.daemon = True
#             self.threads.append(thread)
#             thread.start()
#
#     def add_image(self, image, path):
#         self.queue.put((image, path, "pil"))
#
#     def add_numpy(self, npy, path):
#         self.queue.put((npy, path, "np"))
#
#     def _save_images(self):
#         while True:
#             data, path, tp = self.queue.get()
#             try:
#                 if tp == "pil":
#                     data.save(path)
#                 elif tp == "np":
#                     np.save(path, data)
#             except Exception as e:
#                 print(f"Failed to save {path}: {e}")
#             finally:
#                 self.queue.task_done()
#
#     def join(self):
#         # 阻塞直到所有任务完成
#         self.queue.join()
#         # 停止所有线程
#         for _ in range(self.num_threads):
#             self.queue.put((None, None, None))
#         for thread in self.threads:
#             thread.join()

import threading
import multiprocessing
from multiprocessing import JoinableQueue as MulQueue
from pathlib import Path
from queue import Queue as ThreadQueue
import numpy as np
from PIL import Image
import Globs


class ImageSaver:
    """
    使用多进程执行
    """
    def __init__(self,managerQueue):
        self.managerQueue=managerQueue
        self.num_processes =  Globs.control.ImageSaverWorkNum
        self.type_= Globs.control.ImageSaverThreadType
        if self.type_=="multiprocessing":
            self.queue = MulQueue(maxsize=10)
        else:
            self.queue = ThreadQueue(maxsize=10)
        self.processes = []
        self._initialize_processes()

    def _initialize_processes(self):
        for _ in range(self.num_processes):
            if self.type_=="multiprocessing":
                process = multiprocessing.Process(target=self._save_images,args=(self.queue,))
            else:
                process = threading.Thread(target=self._save_images,args=(self.queue,))
            process.daemon = True
            self.processes.append(process)
            process.start()

    def add(self,obj,path):
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
            data, path, tp = queue.get()
            if data is None:
                break
            try:
                if tp == "pil":
                    Path(path).parent.mkdir(parents=True, exist_ok=True)
                    data.save(path)
                elif tp == "np":
                    np.save(path, data)
            except Exception as e:
                print(f"Failed to save {path}: {e}")
            finally:
                queue.task_done()

    def join(self):
        # 阻塞直到所有任务完成
        self.queue.join()
        # 停止所有进程
        for _ in range(self.num_processes):
            self.queue.put((None, None, None))
        for process in self.processes:
            process.join()
