import json
import logging
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parents[1]
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from Base.utils.nonblocking_logging import configure_nonblocking_logging

CAPTURE_SCRIPT = APP_DIR / "CapAll.py"
HEALTH_URL = os.getenv("LG3D_CAPTURE_HEALTH_URL",
                       "http://127.0.0.1:6100/health")


def _positive_float_env(name: str, default: float) -> float:
    try:
        return max(float(os.getenv(name, str(default))), 0.1)
    except ValueError:
        logging.getLogger(__name__).warning("invalid %s, use default %s", name,
                                            default)
        return default


def _positive_int_env(name: str, default: int) -> int:
    try:
        return max(int(os.getenv(name, str(default))), 1)
    except ValueError:
        logging.getLogger(__name__).warning("invalid %s, use default %s", name,
                                            default)
        return default


CHECK_INTERVAL = _positive_float_env("LG3D_CAPTURE_WATCHDOG_INTERVAL", 5.0)
STARTUP_GRACE = _positive_float_env("LG3D_CAPTURE_STARTUP_GRACE", 45.0)
FAILURE_THRESHOLD = _positive_int_env("LG3D_CAPTURE_FAILURE_THRESHOLD", 3)
RESTART_DELAY = _positive_float_env("LG3D_CAPTURE_RESTART_DELAY", 5.0)
RESTART_MAX_DELAY = _positive_float_env("LG3D_CAPTURE_RESTART_MAX_DELAY",
                                        120.0)
RESTART_STABLE_SECONDS = _positive_float_env(
    "LG3D_CAPTURE_RESTART_STABLE_SECONDS", 300.0)
STOP_TIMEOUT = _positive_float_env("LG3D_CAPTURE_STOP_TIMEOUT", 10.0)


def configure_logging() -> logging.Logger:
    log_dir = Path(os.getenv("LG3D_LOG_DIR", PROJECT_ROOT / "log")) / "CapTrue"
    configure_nonblocking_logging(
        log_dir / "watchdog.log",
        root_level=logging.INFO,
        file_level=logging.INFO,
        console_level=logging.INFO,
    )
    logger = logging.getLogger("capture_watchdog")
    logger.setLevel(logging.INFO)
    return logger


logger = configure_logging()


def acquire_instance_lock():
    """Prevent two watchdogs from creating competing capture processes."""
    if sys.platform != "win32":
        return object()
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = (
        ctypes.c_void_p,
        ctypes.c_bool,
        ctypes.c_wchar_p,
    )
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p, )
    kernel32.CloseHandle.restype = ctypes.c_bool
    handle = kernel32.CreateMutexW(
        None,
        False,
        "Global\\LG3D_Capture_Watchdog",
    )
    if not handle:
        raise OSError("CreateMutexW failed")
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        return None
    return handle


def release_instance_lock(handle):
    if handle is None or sys.platform != "win32":
        return
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p, )
    kernel32.CloseHandle.restype = ctypes.c_bool
    kernel32.CloseHandle(handle)


def capture_service_healthy(url=HEALTH_URL,
                            timeout=2.0,
                            expected_pid=None,
                            expected_token=None) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
            if not (payload.get("ok") is True
                    and payload.get("service") == "CapAll"):
                return False
            if expected_pid is not None:
                try:
                    if int(payload.get("processId", -1)) != int(expected_pid):
                        return False
                except (TypeError, ValueError):
                    return False
            if (expected_token is not None
                    and payload.get("watchdogToken") != expected_token):
                return False
            return True
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return False


def start_capture_process() -> subprocess.Popen:
    logger.info("starting capture service: script=%s", CAPTURE_SCRIPT)
    environment = os.environ.copy()
    watchdog_token = secrets.token_urlsafe(24)
    environment["LG3D_CAPTURE_WATCHDOG_TOKEN"] = watchdog_token
    process = subprocess.Popen(
        [sys.executable, str(CAPTURE_SCRIPT)],
        cwd=APP_DIR,
        env=environment,
    )
    process.lg3d_watchdog_token = watchdog_token
    return process


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
        try:
            process.wait(timeout=STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            logger.critical(
                "capture service remained alive after kill: pid=%s",
                process.pid,
            )


def restart_backoff_seconds(failure_count: int) -> float:
    exponent = max(int(failure_count) - 1, 0)
    return min(max(RESTART_DELAY, 0.0) * 2**min(exponent, 10),
               max(RESTART_MAX_DELAY, RESTART_DELAY, 0.0))


def supervise_capture_process() -> None:
    process = None
    consecutive_failures = 0
    started_at = 0.0
    restart_failures = 0
    try:
        while True:
            if process is None:
                try:
                    process = start_capture_process()
                    started_at = time.monotonic()
                    consecutive_failures = 0
                except Exception as e:
                    restart_failures += 1
                    delay = restart_backoff_seconds(restart_failures)
                    logger.exception(
                        "capture service start failed: attempt=%s retry_in_s=%.1f error=%s",
                        restart_failures,
                        delay,
                        e,
                    )
                    time.sleep(delay)
                    continue

            exit_code = process.poll()
            if exit_code is not None:
                uptime = max(time.monotonic() - started_at, 0.0)
                if uptime >= RESTART_STABLE_SECONDS:
                    restart_failures = 0
                restart_failures += 1
                delay = restart_backoff_seconds(restart_failures)
                logger.error(
                    "capture service exited: pid=%s exit_code=%s uptime_s=%.1f "
                    "restart_attempt=%s retry_in_s=%.1f",
                    process.pid,
                    exit_code,
                    uptime,
                    restart_failures,
                    delay,
                )
                process = None
                time.sleep(delay)
                continue

            time.sleep(CHECK_INTERVAL)
            uptime = max(time.monotonic() - started_at, 0.0)
            if uptime < STARTUP_GRACE:
                continue
            if capture_service_healthy(
                    expected_pid=process.pid,
                    expected_token=getattr(process, "lg3d_watchdog_token",
                                           None)):
                consecutive_failures = 0
                if uptime >= RESTART_STABLE_SECONDS:
                    restart_failures = 0
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
            restart_failures += 1
            delay = restart_backoff_seconds(restart_failures)
            logger.error(
                "capture service restart scheduled after health failure: "
                "attempt=%s retry_in_s=%.1f",
                restart_failures,
                delay,
            )
            time.sleep(delay)
    except KeyboardInterrupt:
        logger.info("capture watchdog shutdown requested")
    finally:
        if process is not None:
            stop_capture_process(process)


if __name__ == "__main__":
    instance_lock = acquire_instance_lock()
    if instance_lock is None:
        logger.error("another capture watchdog is already running; exiting")
    else:
        try:
            supervise_capture_process()
        finally:
            release_instance_lock(instance_lock)
