import logging
from logging.handlers import TimedRotatingFileHandler
import os
import string
import multiprocessing
import Init
from pathlib import Path
import colorlog

# 创建控制台和文件处理器
# 获取日志记录器
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# 清除现有的处理器，防止重复添加
if logger.hasHandlers():
    logger.handlers.clear()

# 创建一个替换标点符号的表，用于进程名称
translator = str.maketrans(string.punctuation, "_" * len(string.punctuation))

# 创建日志目录
log_dir = Init.logDir
Path(log_dir).mkdir(parents=True, exist_ok=True)

# 设置日志文件路径
filename = os.path.join(log_dir, f"%Y-%m-%d_{multiprocessing.current_process().name.translate(translator)}.log")

# 创建文件处理器，按日期进行滚动
file_handler = TimedRotatingFileHandler(filename, when="midnight", interval=1, backupCount=1000)
file_handler.suffix = f"%Y-%m-%d_{multiprocessing.current_process().name.translate(translator)}.log"

# 设置文件日志格式
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                    datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_formatter)

# logger.addHandler(file_handler)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# 使用彩色日志格式输出到控制台
console_formatter = colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

