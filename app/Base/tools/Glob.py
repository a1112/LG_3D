import logging
import subprocess
from queue import Queue
from threading import Thread

logger = logging.getLogger(__name__)


class CmdThread(Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.queue = Queue()
        self.start()

    def put(self, cmd):
        self.queue.put(cmd)

    def run(self):
        while True:
            cmd = self.queue.get()
            try:
                subprocess.run(cmd, shell=True, check=True)
            except subprocess.CalledProcessError as exc:
                logger.warning("command failed: %s returncode=%s", cmd, exc.returncode)
            except Exception as exc:
                logger.exception("command execution failed: %s error=%s", cmd, exc)
            finally:
                self.queue.task_done()


cmdThread = CmdThread()
