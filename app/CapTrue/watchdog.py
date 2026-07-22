import json
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parents[1]
CAPTURE_SCRIPT = APP_DIR / "CapAll.py"
HEALTH_URL = os.getenv("LG3D_CAPTURE_HEALTH_URL",
                       "http://127.0.0.1:6100/health")
CHECK_INTERVAL = float(os.getenv("LG3D_CAPTURE_WATCHDOG_INTERVAL", "5"))
STARTUP_GRACE = float(os.getenv("LG3D_CAPTURE_STARTUP_GRACE", "45"))
FAILURE_THRESHOLD = int(os.getenv("LG3D_CAPTURE_FAILURE_THRESHOLD", "3"))
RESTART_DELAY = float(os.getenv("LG3D_CAPTURE_RESTART_DELAY", "5"))
STOP_TIMEOUT = float(os.getenv("LG3D_CAPTURE_STOP_TIMEOUT", "10"))


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("capture_watchdog")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    log_dir = Path(os.getenv("LG3D_LOG_DIR", PROJECT_ROOT / "log")) / "CapTrue"
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    file_handler = TimedRotatingFileHandler(
        log_dir / "watchdog.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
        delay=True,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


logger = configure_logging()


def capture_service_healthy(url=HEALTH_URL, timeout=2.0) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("ok") is True and payload.get(
                "service") == "CapAll"
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return False


def start_capture_process() -> subprocess.Popen:
    logger.info("starting capture service: script=%s", CAPTURE_SCRIPT)
    return subprocess.Popen(
        [sys.executable, str(CAPTURE_SCRIPT)],
        cwd=APP_DIR,
    )


def stop_capture_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    logger.warning("stopping unhealthy capture service: pid=%s", process.pid)
    process.terminate()
    try:
        process.wait(timeout=STOP_TIMEOUT)
    except subprocess.TimeoutExpired:
        logger.error("capture service did not stop in %.1fs; killing pid=%s",
                     STOP_TIMEOUT, process.pid)
        process.kill()
        process.wait(timeout=STOP_TIMEOUT)


def supervise_capture_process() -> None:
    process = None
    consecutive_failures = 0
    started_at = 0.0
    try:
        while True:
            if process is None or process.poll() is not None:
                if process is not None:
                    logger.error("capture service exited: pid=%s exit_code=%s",
                                 process.pid, process.returncode)
                    time.sleep(RESTART_DELAY)
                process = start_capture_process()
                started_at = time.monotonic()
                consecutive_failures = 0

            time.sleep(CHECK_INTERVAL)
            if time.monotonic() - started_at < STARTUP_GRACE:
                continue
            if capture_service_healthy():
                consecutive_failures = 0
                continue

            consecutive_failures += 1
            logger.warning(
                "capture health check failed: pid=%s failures=%s/%s url=%s",
                process.pid,
                consecutive_failures,
                FAILURE_THRESHOLD,
                HEALTH_URL,
            )
            if consecutive_failures < FAILURE_THRESHOLD:
                continue

            stop_capture_process(process)
            process = None
            consecutive_failures = 0
            time.sleep(RESTART_DELAY)
    except KeyboardInterrupt:
        logger.info("capture watchdog shutdown requested")
    finally:
        if process is not None:
            stop_capture_process(process)


if __name__ == "__main__":
    supervise_capture_process()
