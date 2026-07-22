import logging
import os
from pathlib import Path

import CONFIG
from Base.utils.nonblocking_logging import configure_nonblocking_logging

project_root = Path(__file__).resolve().parents[2]
log_dir = Path(os.getenv("LG3D_LOG_DIR", project_root / "log")) / "CapTrue"
config_name = Path(CONFIG.configFile).stem
filename = log_dir / f"{config_name}_{os.getpid()}.log"

# File and console writes run in separate daemon listeners. Capture, API and
# camera SDK threads only enqueue records and can never wait for console I/O.
logging_runtime = configure_nonblocking_logging(
    filename,
    root_level=logging.DEBUG,
    file_level=logging.DEBUG,
    console_level=logging.INFO,
)
logger = logging.getLogger()
