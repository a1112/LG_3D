import logging
import logging.handlers
from multiprocessing import Process, Queue
from queue import Empty


class LoggerProcess:
    """
    用于管理多进程日志记录的类
    """

    def __init__(self, log_file="app.log", log_level=logging.INFO, queue_timeout=1):
        """
        初始化 LoggerProcess
        :param log_file: 日志文件路径
        :param log_level: 日志级别
        :param queue_timeout: 队列超时时间（秒）
        """
        self.log_file = log_file
        self.log_level = log_level
        self.queue_timeout = queue_timeout
        self.log_queue = Queue()
        self.process = Process(target=self._log_listener)

    def _log_listener(self):
        """
        运行在单独进程中的日志监听器
        """
        handler = logging.FileHandler(self.log_file)
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
        self.process.start()

    def stop(self):
        """
        停止日志进程
        """
        self.log_queue.put(None)  # 通知日志进程退出
        self.process.join()

    def get_logger(self):
        """
        获取一个可用于发送日志的 Logger 对象
        """
        queue_handler = logging.handlers.QueueHandler(self.log_queue)
        logger = logging.getLogger(f"ProcessLogger-{id(self)}")
        logger.setLevel(self.log_level)
        logger.addHandler(queue_handler)
        return logger

