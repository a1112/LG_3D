import logging
import os
import subprocess
from queue import Full, Queue
from threading import Thread

logger = logging.getLogger(__name__)

DEFAULT_CMD_QUEUE_MAXSIZE = 100
CMD_QUEUE_PUT_TIMEOUT = 2.0
DEFAULT_CMD_RUN_TIMEOUT = 30.0


def _get_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default))
    try:
        return max(float(raw_value), 0.1)
    except ValueError:
        logger.warning("invalid %s=%s, use %s", name, raw_value, default)
        return default


def _get_cmd_queue_maxsize() -> int:
    raw_value = os.getenv("LG3D_CMD_QUEUE_MAXSIZE", str(DEFAULT_CMD_QUEUE_MAXSIZE))
    try:
        return max(int(raw_value), 1)
    except ValueError:
        logger.warning("invalid LG3D_CMD_QUEUE_MAXSIZE=%s, use %s", raw_value, DEFAULT_CMD_QUEUE_MAXSIZE)
        return DEFAULT_CMD_QUEUE_MAXSIZE


class CmdThread(Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.queue = Queue(maxsize=_get_cmd_queue_maxsize())
        self.run_timeout = _get_float_env("LG3D_CMD_RUN_TIMEOUT", DEFAULT_CMD_RUN_TIMEOUT)
        self.start()

    def put(self, cmd):
        try:
            self.queue.put(cmd, timeout=CMD_QUEUE_PUT_TIMEOUT)
            return True
        except Full:
            logger.error("command queue full, drop command: %s", cmd)
        return False

    def run(self):
        while True:
            cmd = self.queue.get()
            try:
                subprocess.run(cmd, shell=True, check=True, timeout=self.run_timeout)
            except subprocess.CalledProcessError as exc:
                logger.warning("command failed: %s returncode=%s", cmd, exc.returncode)
            except subprocess.TimeoutExpired:
                logger.error("command timed out after %ss: %s", self.run_timeout, cmd)
            except Exception as exc:
                logger.exception("command execution failed: %s error=%s", cmd, exc)
            finally:
                self.queue.task_done()


cmdThread = CmdThread()
