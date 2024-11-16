import logging
from logging.handlers import TimedRotatingFileHandler
import os
import datetime

import CONFIG

# 创建 logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# 创建控制台处理器
print("采集日志")

# 创建 TimedRotatingFileHandler
log_dir = 'logs/采集/'+CONFIG.configFile.stem
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

filename = os.path.join(log_dir, 'log')
handler = TimedRotatingFileHandler(filename, when="midnight", interval=1, backupCount=1000)
handler.suffix = "%Y-%m-%d.log"

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(handler)
logger.addHandler(console_handler)


