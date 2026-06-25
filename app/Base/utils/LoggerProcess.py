import os
import logging
import logging.handlers
from pathlib import Path
from multiprocessing import Process, Queue
from queue import Empty, Full


DEFAULT_LOG_QUEUE_MAXSIZE = 5000
ERROR_LOG_ENQUEUE_TIMEOUT = 0.2


def _get_log_queue_maxsize() -> int:
    raw_value = os.getenv("LG3D_LOGGER_PROCESS_QUEUE_MAXSIZE", str(DEFAULT_LOG_QUEUE_MAXSIZE))
    try:
        return max(int(raw_value), 1)
    except ValueError:
        logging.getLogger(__name__).warning(
            "invalid LG3D_LOGGER_PROCESS_QUEUE_MAXSIZE=%s, use %s",
            raw_value,
            DEFAULT_LOG_QUEUE_MAXSIZE,
        )
        return DEFAULT_LOG_QUEUE_MAXSIZE


class DroppingQueueHandler(logging.handlers.QueueHandler):
    def enqueue(self, record):
        try:
            self.queue.put_nowait(record)
        except Full:
            if record.levelno < logging.ERROR:
                return
            try:
                self.queue.put(record, timeout=ERROR_LOG_ENQUEUE_TIMEOUT)
            except Full:
                return


class LoggerProcess:
    """
    用于管理多进程日志记录的类
    """

    def __init__(self, log_file="app.log", log_level=logging.INFO, queue_timeout=1, queue_maxsize=None):
        """
        初始化 LoggerProcess
        :param log_file: 日志文件路径
        :param log_level: 日志级别
        :param queue_timeout: 队列超时时间（秒）
        """
        self.log_file = log_file
        self.log_level = log_level
        self.queue_timeout = queue_timeout
        self.queue_maxsize = queue_maxsize or _get_log_queue_maxsize()
        self.log_queue = Queue(maxsize=self.queue_maxsize)
        self.process = Process(target=self._log_listener)

    def _log_listener(self):
        """
        运行在单独进程中的日志监听器
        """
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_path)
        formatter = logging.Formatter('%(asctime)s - %(processName)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        logger = logging.getLogger()
        logger.addHandler(handler)
        logger.setLevel(self.log_level)

        while True:
            try:
                record = self.log_queue.get(timeout=self.queue_timeout)
                if record is None:  # 收到 None 消息时退出
                    break
                logger.handle(record)
            except Empty:
                continue

    def start(self):
        """
        启动日志进程
        """
        if not self.process.is_alive():
            self.process.start()

    def stop(self):
        """
        停止日志进程
        """
        if not self.process.is_alive():
            return
        try:
            self.log_queue.put(None, timeout=self.queue_timeout)
        except Full:
            self.process.terminate()
            self.process.join(timeout=5)
            return
        self.process.join(timeout=5)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=5)

    def get_logger(self):
        """
        获取一个可用于发送日志的 Logger 对象
        """
        queue_handler = DroppingQueueHandler(self.log_queue)
        logger = logging.getLogger(f"ProcessLogger-{id(self)}")
        logger.setLevel(self.log_level)
        logger.propagate = False
        if not any(isinstance(handler, DroppingQueueHandler) for handler in logger.handlers):
            logger.addHandler(queue_handler)
        return logger
