import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

try:
    from . import config
    from .logging_utils import configure_nonblocking_logging
except ImportError:  # pragma: no cover - direct script/PyInstaller execution
    import config
    from logging_utils import configure_nonblocking_logging


APP_DIR = Path(__file__).resolve().parent
MAIN_SCRIPT = APP_DIR / "main.py"
HEALTH_URL = os.getenv(
    "LG3D_PLC_HEALTH_URL",
    f"http://127.0.0.1:{config.server_port}/health",
)


def _positive_float_env(name: str, default: float) -> float:
    try:
        return max(float(os.getenv(name, str(default))), 0.1)
    except ValueError:
        return default


def _positive_int_env(name: str, default: int) -> int:
    try:
        return max(int(os.getenv(name, str(default))), 1)
    except ValueError:
        return default


CHECK_INTERVAL = _positive_float_env("LG3D_PLC_WATCHDOG_INTERVAL", 2.0)
STARTUP_GRACE = _positive_float_env("LG3D_PLC_STARTUP_GRACE", 15.0)
FAILURE_THRESHOLD = _positive_int_env("LG3D_PLC_FAILURE_THRESHOLD", 3)
RESTART_DELAY = _positive_float_env("LG3D_PLC_RESTART_DELAY", 5.0)
RESTART_MAX_DELAY = _positive_float_env("LG3D_PLC_RESTART_MAX_DELAY", 120.0)
RESTART_STABLE_SECONDS = _positive_float_env("LG3D_PLC_RESTART_STABLE_SECONDS", 300.0)
STOP_TIMEOUT = _positive_float_env("LG3D_PLC_STOP_TIMEOUT", 5.0)
WATCHDOG_MUTEX_NAME = "Global\\LG3D_PLC_Watchdog"

logger = logging.getLogger("plc_watchdog")


def configure_logging() -> None:
    configure_nonblocking_logging(APP_DIR / "log" / "plc_watchdog.log")
    logger.setLevel(logging.INFO)


def acquire_instance_lock():
    """Prevent competing watchdogs from repeatedly replacing each other's child."""
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
    handle = kernel32.CreateMutexW(None, False, WATCHDOG_MUTEX_NAME)
    if not handle:
        raise OSError("CreateMutexW failed for PLC watchdog")
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        return None
    return handle


def release_instance_lock(handle) -> None:
    if handle is None or sys.platform != "win32":
        return
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p, )
    kernel32.CloseHandle.restype = ctypes.c_bool
    kernel32.CloseHandle(handle)


def plc_service_healthy(url: str = HEALTH_URL, timeout: float = 2.0) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
            return (
                isinstance(payload, dict)
                and payload.get("service") == "ok"
                and payload.get("stuck") is not True
            )
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return False


def restart_backoff_seconds(failure_count: int) -> float:
    exponent = max(int(failure_count) - 1, 0)
    return min(
        RESTART_DELAY * 2**min(exponent, 10),
        max(RESTART_MAX_DELAY, RESTART_DELAY),
    )


def start_plc_process() -> subprocess.Popen:
    logger.info("starting PLC bridge: script=%s", MAIN_SCRIPT)
    environment = os.environ.copy()
    environment["LG3D_PLC_WATCHDOG_CHILD"] = "1"
    return subprocess.Popen(
        [sys.executable, str(MAIN_SCRIPT)],
        cwd=APP_DIR,
        env=environment,
    )


def stop_plc_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    logger.warning("stopping unhealthy PLC bridge: pid=%s", process.pid)
    process.terminate()
    try:
        process.wait(timeout=STOP_TIMEOUT)
    except subprocess.TimeoutExpired:
        logger.error("PLC bridge did not stop in %.1fs; killing pid=%s", STOP_TIMEOUT, process.pid)
        process.kill()
        try:
            process.wait(timeout=STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            logger.critical("PLC bridge remained alive after kill: pid=%s", process.pid)


def supervise_plc_process() -> None:
    process = None
    consecutive_failures = 0
    restart_failures = 0
    started_at = 0.0
    try:
        while True:
            if process is None:
                try:
                    process = start_plc_process()
                    started_at = time.monotonic()
                    consecutive_failures = 0
                except Exception as error:
                    restart_failures += 1
                    delay = restart_backoff_seconds(restart_failures)
                    logger.exception(
                        "PLC bridge start failed: attempt=%s retry_in_s=%.1f error=%s",
                        restart_failures,
                        delay,
                        error,
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
                    "PLC bridge exited: pid=%s exit_code=%s uptime_s=%.1f "
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
            if plc_service_healthy():
                consecutive_failures = 0
                if uptime >= RESTART_STABLE_SECONDS:
                    restart_failures = 0
                continue

            consecutive_failures += 1
            logger.warning(
                "PLC health check failed: pid=%s failures=%s/%s url=%s",
                process.pid,
                consecutive_failures,
                FAILURE_THRESHOLD,
                HEALTH_URL,
            )
            if consecutive_failures < FAILURE_THRESHOLD:
                continue

            stop_plc_process(process)
            process = None
            consecutive_failures = 0
            restart_failures += 1
            delay = restart_backoff_seconds(restart_failures)
            logger.error(
                "PLC bridge restart scheduled after health failure: "
                "attempt=%s retry_in_s=%.1f",
                restart_failures,
                delay,
            )
            time.sleep(delay)
    except KeyboardInterrupt:
        logger.info("PLC watchdog shutdown requested")
    finally:
        if process is not None:
            stop_plc_process(process)


def main() -> None:
    configure_logging()
    instance_lock = acquire_instance_lock()
    if instance_lock is None:
        logger.error("another PLC watchdog is already running; exiting")
        return
    try:
        supervise_plc_process()
    finally:
        release_instance_lock(instance_lock)


if __name__ == "__main__":
    main()
