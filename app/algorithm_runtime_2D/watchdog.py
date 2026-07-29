"""External supervisor for the 2D algorithm process.

The 2D worker graph uses threads for normal cancellation.  A native
YOLO/OpenCV/Torch call cannot be forcefully stopped by a Python thread, so this
separate process replaces the complete worker tree after a sustained heartbeat
failure or an overdue registered activity.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any


APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parents[1]
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from Base.utils.nonblocking_logging import configure_nonblocking_logging


SERVICE_NAME = "LG3D_ALGORITHM_2D"
ENTRYPOINT = os.getenv("LG3D_ALGORITHM_2D_ENTRYPOINT", "server.py")
ALGORITHM_SCRIPT = APP_DIR / ENTRYPOINT
HEARTBEAT_FILE_ENV = "LG3D_ALGORITHM_2D_HEARTBEAT_FILE"
HEARTBEAT_FILE = Path(
    os.getenv(HEARTBEAT_FILE_ENV, APP_DIR / "log" / "runtime_heartbeat.json")
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


CHECK_INTERVAL = _positive_float_env("LG3D_ALGORITHM_2D_WATCHDOG_INTERVAL", 5.0)
STARTUP_GRACE = _positive_float_env("LG3D_ALGORITHM_2D_STARTUP_GRACE", 600.0)
HEARTBEAT_TIMEOUT = _positive_float_env(
    "LG3D_ALGORITHM_2D_HEARTBEAT_TIMEOUT", 30.0
)
FAILURE_THRESHOLD = _positive_int_env(
    "LG3D_ALGORITHM_2D_FAILURE_THRESHOLD", 3
)
RESTART_DELAY = _positive_float_env("LG3D_ALGORITHM_2D_RESTART_DELAY", 5.0)
RESTART_MAX_DELAY = _positive_float_env(
    "LG3D_ALGORITHM_2D_RESTART_MAX_DELAY", 300.0
)
RESTART_STABLE_SECONDS = _positive_float_env(
    "LG3D_ALGORITHM_2D_RESTART_STABLE_SECONDS", 300.0
)
STOP_TIMEOUT = _positive_float_env("LG3D_ALGORITHM_2D_STOP_TIMEOUT", 15.0)
MAX_FUTURE_SKEW = 300.0


def configure_logging() -> logging.Logger:
    log_dir = Path(os.getenv("LG3D_LOG_DIR", PROJECT_ROOT / "log")) / "Algorithm2D"
    configure_nonblocking_logging(
        log_dir / "watchdog.log",
        root_level=logging.INFO,
        file_level=logging.INFO,
        console_level=logging.INFO,
    )
    result = logging.getLogger("algorithm_2d_watchdog")
    result.setLevel(logging.INFO)
    return result


logger = configure_logging()


def restart_backoff_seconds(failure_count: int) -> float:
    exponent = max(int(failure_count) - 1, 0)
    return min(
        RESTART_DELAY * (2 ** min(exponent, 10)),
        max(RESTART_MAX_DELAY, RESTART_DELAY),
    )


def read_heartbeat(path: Path = HEARTBEAT_FILE) -> dict[str, Any] | None:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def heartbeat_health(
    process,
    *,
    path: Path = HEARTBEAT_FILE,
    now: float | None = None,
) -> tuple[bool, str]:
    payload = read_heartbeat(path)
    if payload is None:
        return False, "heartbeat_missing_or_invalid"
    if payload.get("service") != SERVICE_NAME:
        return False, "heartbeat_service_mismatch"
    try:
        heartbeat_pid = int(payload.get("pid"))
        updated_at = float(payload.get("updatedAtEpoch"))
    except (TypeError, ValueError):
        return False, "heartbeat_fields_invalid"
    if heartbeat_pid != int(process.pid):
        return False, "heartbeat_pid_mismatch"

    now = time.time() if now is None else float(now)
    age = now - updated_at
    if age < -MAX_FUTURE_SKEW:
        return False, "heartbeat_clock_invalid"
    if age > HEARTBEAT_TIMEOUT:
        return False, f"heartbeat_stale:{age:.1f}s"

    activities = payload.get("activities", [])
    if not isinstance(activities, list):
        return False, "heartbeat_activities_invalid"
    for activity in activities:
        try:
            deadline = float(activity["deadlineAtEpoch"])
        except (KeyError, TypeError, ValueError):
            return False, "heartbeat_activity_invalid"
        if now > deadline:
            return False, "activity_overdue:%s:%s" % (
                activity.get("name", "unknown"),
                activity.get("workId", "unknown"),
            )
    if payload.get("status") != "ok":
        return False, f"heartbeat_status:{payload.get('status')}"
    return True, "ok"


def start_algorithm_process() -> subprocess.Popen:
    if ALGORITHM_SCRIPT.name not in {"server.py", "main2d.py"}:
        raise ValueError(
            "LG3D_ALGORITHM_2D_ENTRYPOINT must be server.py or main2d.py"
        )
    try:
        HEARTBEAT_FILE.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("could not remove old 2D heartbeat: %s", exc)
    env = os.environ.copy()
    env[HEARTBEAT_FILE_ENV] = str(HEARTBEAT_FILE)
    env["LG3D_ALGORITHM_2D_WATCHDOG_CHILD"] = "1"
    logger.info("starting 2D algorithm service: script=%s", ALGORITHM_SCRIPT)
    kwargs = {
        "cwd": APP_DIR,
        "env": env,
    }
    if sys.platform != "win32":
        kwargs["start_new_session"] = True
    return subprocess.Popen([sys.executable, str(ALGORITHM_SCRIPT)], **kwargs)


def _force_kill_process_tree(process) -> None:
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
            if result.returncode != 0:
                logger.error(
                    "taskkill failed for 2D algorithm pid=%s: %s",
                    process.pid,
                    (result.stderr or result.stdout).strip(),
                )
                process.kill()
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.error("2D process tree kill failed pid=%s: %s", process.pid, exc)
            process.kill()
        return

    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        process.kill()


def stop_algorithm_process(process) -> None:
    if process.poll() is not None:
        return
    logger.warning("stopping unhealthy 2D algorithm service: pid=%s", process.pid)
    if sys.platform == "win32":
        _force_kill_process_tree(process)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            process.terminate()
    try:
        process.wait(timeout=STOP_TIMEOUT)
    except subprocess.TimeoutExpired:
        logger.error(
            "2D algorithm did not stop in %.1fs; killing tree pid=%s",
            STOP_TIMEOUT,
            process.pid,
        )
        _force_kill_process_tree(process)
        try:
            process.wait(timeout=STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            logger.critical("2D algorithm remained alive after kill pid=%s", process.pid)


def acquire_instance_lock():
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
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel32.CloseHandle.restype = ctypes.c_bool
    handle = kernel32.CreateMutexW(None, False,
                                   "Global\\LG3D_Algorithm2D_Watchdog")
    if not handle:
        raise OSError("CreateMutexW failed")
    if kernel32.GetLastError() == 183:
        kernel32.CloseHandle(handle)
        return None
    return handle


def release_instance_lock(handle) -> None:
    if handle is None or sys.platform != "win32":
        return
    import ctypes

    ctypes.windll.kernel32.CloseHandle(handle)


def supervise_algorithm_process() -> None:
    process = None
    consecutive_failures = 0
    restart_failures = 0
    started_at = 0.0
    try:
        while True:
            if process is None:
                try:
                    process = start_algorithm_process()
                    started_at = time.monotonic()
                    consecutive_failures = 0
                except Exception as exc:
                    restart_failures += 1
                    delay = restart_backoff_seconds(restart_failures)
                    logger.exception(
                        "2D algorithm start failed: attempt=%s retry_in=%.1fs error=%s",
                        restart_failures,
                        delay,
                        exc,
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
                    "2D algorithm exited: pid=%s exit_code=%s uptime=%.1fs "
                    "restart_attempt=%s retry_in=%.1fs",
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

            healthy, reason = heartbeat_health(process)
            if healthy:
                consecutive_failures = 0
                if uptime >= RESTART_STABLE_SECONDS:
                    restart_failures = 0
                continue

            consecutive_failures += 1
            logger.warning(
                "2D algorithm health failed: pid=%s failures=%s/%s reason=%s",
                process.pid,
                consecutive_failures,
                FAILURE_THRESHOLD,
                reason,
            )
            if consecutive_failures < FAILURE_THRESHOLD:
                continue

            stop_algorithm_process(process)
            process = None
            consecutive_failures = 0
            restart_failures += 1
            delay = restart_backoff_seconds(restart_failures)
            logger.error(
                "2D algorithm restart scheduled: attempt=%s retry_in=%.1fs",
                restart_failures,
                delay,
            )
            time.sleep(delay)
    except KeyboardInterrupt:
        logger.info("2D algorithm watchdog shutdown requested")
    finally:
        if process is not None:
            stop_algorithm_process(process)


if __name__ == "__main__":
    instance_lock = acquire_instance_lock()
    if instance_lock is None:
        logger.error("another 2D algorithm watchdog is already running; exiting")
    else:
        try:
            supervise_algorithm_process()
        finally:
            release_instance_lock(instance_lock)
