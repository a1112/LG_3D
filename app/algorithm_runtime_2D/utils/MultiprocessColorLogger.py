import logging
import os
import sys
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from multiprocessing import Queue
import colorlog
from typing import Optional, Dict, Any
from pathlib import Path
from configs import CONFIG

class EnhancedMultiProcessLogger:
    """
    增强版多进程安全日志记录器

    功能特性：
    1. 多进程安全的日志记录
    2. 彩色控制台输出（基于colorlog）
    3. 自动轮转的日志文件保存
    4. 可自定义日志格式和颜色
    5. 支持日志文件按大小和时间轮转
    6. 线程安全设计
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
            self,
            name: str = "app",
            log_level: str = "INFO",
            console_output: bool = True,
            log_to_file: bool = True,
            log_dir: str = CONFIG.loger_folder,
            log_filename: str = CONFIG.loger_file,
            max_bytes: int = 10 * 1024 * 1024,  # 10MB
            backup_count: int = 5,
            use_color: bool = True,
            log_format: Optional[str] = None,
            color_map: Optional[Dict[str, str]] = None,
            file_log_format: Optional[str] = None,
            when: str = "midnight",  # 按时间轮转的时间单位
            interval: int = 1,  # 轮转间隔
            encoding: str = "utf-8"
    ):
        if getattr(self, '_initialized', False):
            return

        # 初始化配置
        self.name = name
        self.log_level = log_level
        self.console_output = console_output
        self.log_to_file = log_to_file
        self.log_dir = log_dir
        self.log_filename = log_filename
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.use_color = use_color
        self.when = when
        self.interval = interval
        self.encoding = encoding

        # 日志格式设置
        self.log_format = log_format or (
            "%(log_color)s%(asctime)s [%(process)d:%(thread)d] %(levelname)-8s %(name)-15s - %(message)s"
        )
        self.file_log_format = file_log_format or (
            "%(asctime)s [%(process)d:%(thread)d] %(levelname)-8s %(name)-15s - %(message)s"
        )

        # 颜色映射
        self.color_map = color_map or {
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }

        # 创建日志目录
        if self.log_to_file:
            Path(self.log_dir).mkdir(parents=True, exist_ok=True)

        # 设置日志系统
        self._setup_logging_system()
        self._initialized = True

    def _setup_logging_system(self):
        """初始化日志系统"""
        # 创建主记录器
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.log_level)
        self.logger.propagate = False

        # 清除所有现有处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # 创建处理器列表
        handlers = []

        # 控制台处理器
        if self.console_output:
            console_handler = self._create_console_handler()
            handlers.append(console_handler)

        # 文件处理器
        if self.log_to_file:
            file_handler = self._create_file_handler()
            handlers.append(file_handler)

        # 创建多进程队列和监听器
        self.log_queue = Queue(-1)  # 无界队列
        self.queue_listener = QueueListener(self.log_queue, *handlers)
        self.queue_listener.start()

        # 为主记录器添加处理器（主进程直接记录）
        for handler in handlers:
            self.logger.addHandler(handler)

    def _create_console_handler(self) -> logging.Handler:
        """创建彩色控制台处理器"""
        if self.use_color:
            formatter = colorlog.ColoredFormatter(
                self.log_format,
                log_colors=self.color_map,
                reset=True,
                style='%'
            )
            handler = colorlog.StreamHandler(sys.stdout)
        else:
            formatter = logging.Formatter(
                self.log_format.replace("%(log_color)s", ""),
                style='%'
            )
            handler = logging.StreamHandler(sys.stdout)

        handler.setFormatter(formatter)
        handler.setLevel(self.log_level)
        return handler

    def _create_file_handler(self) -> logging.Handler:
        """创建文件处理器，支持按大小和时间轮转"""
        log_path = Path(self.log_dir) / self.log_filename

        # 使用TimedRotatingFileHandler按时间轮转
        if self.when:
            from logging.handlers import TimedRotatingFileHandler
            handler = TimedRotatingFileHandler(
                filename=str(log_path),
                when=self.when,
                interval=self.interval,
                backupCount=self.backup_count,
                encoding=self.encoding
            )
        # 使用RotatingFileHandler按大小轮转
        else:
            handler = RotatingFileHandler(
                filename=str(log_path),
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding=self.encoding
            )

        formatter = logging.Formatter(
            self.file_log_format,
            style='%'
        )
        handler.setFormatter(formatter)
        handler.setLevel(self.log_level)
        return handler

    def get_process_logger(self) -> logging.Logger:
        """
        获取适用于子进程的记录器
        子进程应该使用此方法获取记录器
        """
        handler = QueueHandler(self.log_queue)
        logger = logging.getLogger(self.name)
        logger.setLevel(self.log_level)

        # 清除所有现有处理器
        for h in logger.handlers[:]:
            logger.removeHandler(h)

        logger.addHandler(handler)
        return logger

    def shutdown(self):
        """优雅关闭日志系统"""
        self.queue_listener.stop()
        logging.shutdown()

    @classmethod
    def get_logger(cls) -> logging.Logger:
        """获取主记录器"""
        if not cls._instance or not getattr(cls._instance, '_initialized', False):
            raise RuntimeError("Logger not initialized. Call EnhancedMultiProcessLogger() first.")
        return cls._instance.logger

_logger_ = EnhancedMultiProcessLogger(
    name="my_app",
    log_level="DEBUG",
    console_output=True,
    log_to_file = False,
    log_dir = CONFIG.loger_folder,
    log_filename = CONFIG.loger_file,
    max_bytes=5 * 1024 * 1024,  # 5MB
    backup_count=7,
    use_color=True,
    when="midnight",  # 每天轮转
    interval=1
)
logger = _logger_.get_logger()
# 使用示例
if __name__ == "__main__":
    # 在主进程中初始化日志系统

    # 获取主记录器
    main_logger = EnhancedMultiProcessLogger.get_logger()

    # 记录不同级别的日志
    main_logger.debug("This is a debug message (main process)")
    main_logger.info("This is an info message (main process)")
    main_logger.warning("This is a warning message (main process)")
    main_logger.error("This is an error message (main process)")
    main_logger.critical("This is a critical message (main process)")


    # 在子进程中使用
    from multiprocessing import Process


    def worker(worker_id):
        # 获取子进程记录器
        worker_logger = EnhancedMultiProcessLogger().get_process_logger()
        worker_logger.info(f"Worker {worker_id} started")
        worker_logger.warning(f"Worker {worker_id} encountered a minor issue")
        worker_logger.error(f"Worker {worker_id} failed to complete task")


    processes = [Process(target=worker, args=(i,)) for i in range(3)]
    for p in processes:
        p.start()
    for p in processes:
        p.join()

    # 关闭日志系统
    EnhancedMultiProcessLogger().shutdown()
    print("Logging system shutdown completed.")
