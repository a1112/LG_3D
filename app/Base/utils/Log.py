import logging
import multiprocessing
import os
from pathlib import Path
import string

from Base import Init
from Base.utils.nonblocking_logging import configure_nonblocking_logging


translator = str.maketrans(string.punctuation,
                           "_" * len(string.punctuation))
process_name = multiprocessing.current_process().name.translate(translator)
project_root = Path(__file__).resolve().parents[3]
configured_log_dir = Path(Init.logDir)
if not configured_log_dir.is_absolute():
    configured_log_dir = project_root / configured_log_dir
log_dir = Path(os.getenv("LG3D_LOG_DIR", configured_log_dir)) / "Algorithm"

# Algorithm stages emit a large amount of diagnostic output. Business threads
# only enqueue records; a paused console or slow disk cannot hold the GIL or a
# logging handler lock in the processing pipeline.
logging_runtime = configure_nonblocking_logging(
    log_dir / f"{process_name}_{os.getpid()}.log",
    root_level=logging.DEBUG,
    file_level=logging.DEBUG,
    console_level=logging.INFO,
)
logger = logging.getLogger()

for noisy_logger in ("matplotlib", "ultralytics", "asyncio", "PIL"):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

try:
    from ultralytics.utils import LOGGER as _ULTRA_LOGGER

    _ULTRA_LOGGER.setLevel(logging.WARNING)
except Exception:
    pass
