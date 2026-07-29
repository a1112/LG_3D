import json
import logging
import os
from pathlib import Path
import signal
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


API_SCRIPT = APP_DIR / "Server.py"
HEALTH_URL = os.getenv("LG3D_API_HEALTH_URL", "http://127.0.0.1:5010/health")


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


CHECK_INTERVAL = _positive_float_env("LG3D_API_WATCHDOG_INTERVAL", 5.0)
STARTUP_GRACE = _positive_float_env("LG3D_API_STARTUP_GRACE", 45.0)
FAILURE_THRESHOLD = _positive_int_env("LG3D_API_FAILURE_THRESHOLD", 3)
RESTART_DELAY = _positive_float_env("LG3D_API_RESTART_DELAY", 5.0)
RESTART_MAX_DELAY = _positive_float_env("LG3D_API_RESTART_MAX_DELAY", 300.0)
RESTART_STABLE_SECONDS = _positive_float_env(
    "LG3D_API_RESTART_STABLE_SECONDS", 300.0)
STOP_TIMEOUT = _positive_float_env("LG3D_API_STOP_TIMEOUT", 10.0)


def configure_logging() -> logging.Logger:
    log_dir = Path(os.getenv("LG3D_LOG_DIR", PROJECT_ROOT / "log")) / "Server"
    configure_nonblocking_logging(
        log_dir / "watchdog.log",
        root_level=logging.INFO,
        file_level=logging.INFO,
        console_level=logging.INFO,
    )
    logger = logging.getLogger("api_watchdog")
    logger.setLevel(logging.INFO)
    return logger


logger = configure_logging()


def acquire_instance_lock():
    """Prevent competing watchdogs from creating multiple API processes."""
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
    # The UI/service may be launched from another RDP or Windows service
    # session.  A global mutex prevents two supervisors from alternately
    # replacing the same port-bound process across sessions.
    handle = kernel32.CreateMutexW(None, False, "Global\\LG3D_API_Watchdog")
    if not handle:
        raise OSError("CreateMutexW failed")
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        return None
    return handle


def release_instance_lock(handle) -> None:
    if handle is None or sys.platform != "win32":
        return
    import ctypes

    ctypes.windll.kernel32.CloseHandle(handle)


def restart_backoff(failures: int) -> float:
    exponent = max(int(failures) - 1, 0)
    return min(RESTART_DELAY * (2**min(exponent, 10)), RESTART_MAX_DELAY)


def api_service_healthy(url=HEALTH_URL, timeout=2.0) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("ok") is True and payload.get(
                "service") == "LG3D_API"
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return False


def start_api_process() -> subprocess.Popen:
    logger.info("starting API service: script=%s", API_SCRIPT)
    environment = os.environ.copy()
    environment["LG3D_API_WATCHDOG_CHILD"] = "1"
    kwargs = {"cwd": APP_DIR, "env": environment}
    if sys.platform != "win32":
        kwargs["start_new_session"] = True
    return subprocess.Popen([sys.executable, str(API_SCRIPT)], **kwargs)


def _force_kill_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True,
                text=True,
                timeout=STOP_TIMEOUT,
            )
            if result.returncode == 0:
                return
            logger.error(
                "taskkill failed for API pid=%s: %s",
                process.pid,
                (result.stderr or result.stdout).strip(),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.error("API process tree kill failed pid=%s: %s",
                         process.pid, exc)
        process.kill()
        return

    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        process.kill()


def stop_api_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    logger.warning("stopping unhealthy API service: pid=%s", process.pid)

    # On Windows, Popen.terminate() maps to TerminateProcess.  Once the parent
    # exits successfully there is no later opportunity to discover and stop
    # its Uvicorn/Rust descendants, so terminate the complete tree first.
    if sys.platform == "win32":
        _force_kill_process_tree(process)
        try:
            process.wait(timeout=STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            logger.critical("API service tree remained alive after kill: pid=%s",
                            process.pid)
        return

    process.terminate()
    try:
        process.wait(timeout=STOP_TIMEOUT)
    except subprocess.TimeoutExpired:
        logger.error("API service did not stop in %.1fs; killing tree pid=%s",
                     STOP_TIMEOUT, process.pid)
        _force_kill_process_tree(process)
        try:
            process.wait(timeout=STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            logger.critical("API service remained alive after kill: pid=%s",
                            process.pid)


def supervise_api_process() -> None:
    process = None
    consecutive_failures = 0
    restart_failures = 0
    started_at = 0.0
    try:
        while True:
            if process is None or process.poll() is not None:
                if process is not None:
                    logger.error("API service exited: pid=%s exit_code=%s",
                                 process.pid, process.returncode)
                    restart_failures += 1
                    delay = restart_backoff(restart_failures)
                    logger.warning(
                        "API restart backoff after exit: failures=%s delay=%.1fs",
                        restart_failures,
                        delay,
                    )
                    time.sleep(delay)
                try:
                    process = start_api_process()
                except Exception as exc:
                    restart_failures += 1
                    delay = restart_backoff(restart_failures)
                    logger.exception(
                        "API process failed to start: failures=%s "
                        "retry_in=%.1fs error=%s",
                        restart_failures,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
                    process = None
                    continue
                started_at = time.monotonic()
                consecutive_failures = 0

            time.sleep(CHECK_INTERVAL)
            if time.monotonic() - started_at < STARTUP_GRACE:
                continue
            if api_service_healthy():
                consecutive_failures = 0
                if (restart_failures
                        and time.monotonic() - started_at
                        >= RESTART_STABLE_SECONDS):
                    logger.info(
                        "API service stable for %.1fs; reset restart backoff",
                        RESTART_STABLE_SECONDS,
                    )
                    restart_failures = 0
                continue

            consecutive_failures += 1
            logger.warning(
                "API health check failed: pid=%s failures=%s/%s url=%s",
                process.pid,
                consecutive_failures,
                FAILURE_THRESHOLD,
                HEALTH_URL,
            )
            if consecutive_failures < FAILURE_THRESHOLD:
                continue

            stop_api_process(process)
            process = None
            consecutive_failures = 0
            restart_failures += 1
            delay = restart_backoff(restart_failures)
            logger.warning(
                "API restart backoff after failed health checks: "
                "failures=%s delay=%.1fs",
                restart_failures,
                delay,
            )
            time.sleep(delay)
    except KeyboardInterrupt:
        logger.info("API watchdog shutdown requested")
    finally:
        if process is not None:
            stop_api_process(process)


if __name__ == "__main__":
    instance_lock = acquire_instance_lock()
    if instance_lock is None:
        logger.error("another API watchdog is already running; exiting")
    else:
        try:
            supervise_api_process()
        finally:
            release_instance_lock(instance_lock)
