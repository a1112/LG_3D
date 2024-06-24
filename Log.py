import logging
import os
from datetime import datetime


# 创建日志目录


class DailyLogger:
    def __init__(self, log_dir):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.logger = None
        self.current_date = None
        self.setup_logger()

    def setup_logger(self):
        """设置基于当前日期的新日志文件。"""
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self.current_date:
            self.current_date = today
            log_file_path = os.path.join(self.log_dir, f"{today}.log")
            # 创建一个新的logger实例
            self.logger = logging.getLogger(today)
            self.logger.setLevel(logging.INFO)
            # 创建FileHandler
            file_handler = logging.FileHandler(log_file_path)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            # 清理现有的handlers
            self.logger.handlers.clear()
            # 添加新的handler
            self.logger.addHandler(file_handler)

    def log(self, message, level="info"):
        """记录日志，同时确保日志文件是最新的。"""
        print(f" {level}  {message}")
        self.setup_logger()
        if level == 'info':
            self.logger.info(message)
        elif level == 'debug':
            self.logger.debug(message)
        elif level == 'warning':
            self.logger.warning(message)
        elif level == 'error':
            self.logger.error(message)
        elif level == 'critical':
            self.logger.critical(message)

    def info(self, message):
        self.log(message, "info")

    def debug(self, message):
        self.log(message, "debug")

    def warning(self, message):
        self.log(message, "warning")

    def error(self, message):
        self.log(message, "error")

    def critical(self, message):
        self.log(message, "critical")
