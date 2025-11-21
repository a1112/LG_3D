import logging
from logging.handlers import TimedRotatingFileHandler
import os
import datetime
from pathlib import Path
import CONFIG

# 创建 logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# 创建控制台处理器
print("采集日志")
log_dir_base = Path("log")
# 创建 TimedRotatingFileHandler
log_dir = log_dir_base/"CapTrue"/f"{CONFIG.configFile.stem}_{os.getpid()}"

log_dir_base.mkdir(parents=True, exist_ok=True)

filename = str(log_dir)
handler = TimedRotatingFileHandler(filename, when="midnight", interval=1, backupCount=1000)
handler.suffix = "%Y-%m-%d.log"
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# logger.addHandler(handler)
logger.addHandler(console_handler)
