import logging
import os
from pathlib import Path
import sys


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from Base.utils.nonblocking_logging import configure_nonblocking_logging

# 屏蔽 PIL 的 DEBUG 日志
logging.getLogger('PIL').setLevel(logging.WARNING)
logging.getLogger('PIL.PngImagePlugin').setLevel(logging.WARNING)
logging.getLogger('PIL.Image').setLevel(logging.WARNING)

project_root = APP_ROOT.parent
log_dir = Path(os.getenv("LG3D_LOG_DIR", project_root / "log")) / "Communication"
logging_runtime = configure_nonblocking_logging(
    log_dir / f"TcpServer_{os.getpid()}.log",
    root_level=logging.DEBUG,
    file_level=logging.DEBUG,
    console_level=logging.INFO,
)
logger = logging.getLogger()


