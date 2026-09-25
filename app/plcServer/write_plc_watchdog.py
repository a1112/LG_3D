"""External watchdog for the PLC width/database writer."""
from __future__ import annotations

import json
import logging
import math
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any


def _runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _runtime_dir()
APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from Base.utils.Singleton import SingletonLock

try:
    from .logging_utils import configure_nonblocking_logging
    from .plc_writer_heartbeat import SERVICE_NAME, WATCHDOG_PID_ENV, WATCHDOG_TOKEN_ENV
except ImportError:  # pragma: no cover - direct script/PyInstaller execution
    from logging_utils import configure_nonblocking_logging
    from plc_writer_heartbeat import SERVICE_NAME, WATCHDOG_PID_ENV, WATCHDOG_TOKEN_ENV


WRITE_SCRIPT = Path(__file__).resolve().with_name("writePLC.py")
CHILD_ENVIRONMENT = "LG3D_PLC_WRITER_WATCHDOG_CHILD"
HEARTBEAT_FILE_ENV = "LG3D_PLC_WRITER_HEARTBEAT_FILE"


def _positive_float_env(name: str, default: float) -> float:
    try:
        return max(float(os.getenv(name, str(default))), 0.1)
    except (TypeError, ValueError):
        return default


def _positive_int_env(name: str, default: int) -> int:
    try:
        return max(int(os.getenv(name, str(default))), 1)
    except (TypeError, ValueError):
        return default


HEARTBEAT_FILE = Path(
    os.getenv(
        HEARTBEAT_FILE_ENV,
        str(APP_DIR / "log" / "plc_writer_heartbeat.json"),
    )
)
CHECK_INTERVAL = _positive_float_env("LG3D_PLC_WRITER_WATCHDOG_INTERVAL", 2.0)
HEARTBEAT_TIMEOUT = _positive_float_env("LG3D_PLC_WRITER_HEARTBEAT_TIMEOUT", 10.0)
STARTUP_GRACE = _positive_float_env("LG3D_PLC_WRITER_STARTUP_GRACE", 60.0)
FAILURE_THRESHOLD = _positive_int_env("LG3D_PLC_WRITER_FAILURE_THRESHOLD", 3)
RESTART_DELAY = _positive_float_env("LG3D_PLC_WRITER_RESTART_DELAY", 5.0)
RESTART_MAX_DELAY = _positive_float_env("LG3D_PLC_WRITER_RESTART_MAX_DELAY", 120.0)
RESTART_STABLE_SECONDS = _positive_float_env(
    "LG3D_PLC_WRITER_RESTART_STABLE_SECONDS",
    300.0,
)
STOP_TIMEOUT = _positive_float_env("LG3D_PLC_WRITER_STOP_TIMEOUT", 5.0)
FUTURE_CLOCK_TOLERANCE = _positive_float_env(
    "LG3D_PLC_WRITER_FUTURE_CLOCK_TOLERANCE",
    30.0,
)

logger = logging.getLogger("plc_writer_watchdog")


def configure_logging() -> None:
    configure_nonblocking_logging(APP_DIR / "log" / "plc_writer_watchdog.log")
    logger.setLevel(logging.INFO)


def read_heartbeat(path: Path = HEARTBEAT_FILE) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def heartbeat_health(
    process: subprocess.Popen,
    expected_token: str,
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
        heartbeat_pid = int(payload["pid"])
        updated_at = float(payload["updatedAtEpoch"])
    except (KeyError, TypeError, ValueError):
        return False, "heartbeat_fields_invalid"
    if heartbeat_pid != int(process.pid):
        return False, "heartbeat_pid_mismatch"
    if payload.get("watchdogToken") != expected_token:
        return False, "heartbeat_token_mismatch"
    if not math.isfinite(updated_at):
        return False, "heartbeat_clock_invalid"

    current_time = time.time() if now is None else float(now)
    age = current_time - updated_at
    if age < -FUTURE_CLOCK_TOLERANCE:
        return False, "heartbeat_clock_in_future"
    if age > HEARTBEAT_TIMEOUT:
        return False, f"heartbeat_stale:{age:.1f}s"

    activities = payload.get("activities")
    if not isinstance(activities, list):
        return False, "heartbeat_activities_invalid"
    for activity in activities:
        if not isinstance(activity, dict):
            return False, "heartbeat_activity_invalid"
        try:
            deadline = float(activity["deadlineAtEpoch"])
        except (KeyError, TypeError, ValueError):
            return False, "heartbeat_activity_invalid"
        if not math.isfinite(deadline):
            return False, "heartbeat_activity_invalid"
        if current_time > deadline:
            name = str(activity.get("name", "unknown"))[:128]
            return False, f"heartbeat_activity_overdue:{name}"
    if payload.get("status") != "ok":
        return False, f"heartbeat_status:{payload.get('status')}"
    return True, "ok"


def restart_backoff_seconds(failure_count: int) -> float:
    exponent = max(int(failure_count) - 1, 0)
    return min(
        RESTART_DELAY * 2 ** min(exponent, 10),
        max(RESTART_MAX_DELAY, RESTART_DELAY),
    )


def _writer_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, str(WRITE_SCRIPT)]


def remove_old_heartbeat() -> None:
    try:
        HEARTBEAT_FILE.unlink(missing_ok=True)
    except OSError as error:
        logger.warning("could not remove old PLC writer heartbeat: %s", error)


def start_writer_process() -> subprocess.Popen:
    remove_old_heartbeat()
    environment = os.environ.copy()
    watchdog_token = uuid.uuid4().hex
    environment[CHILD_ENVIRONMENT] = "1"
    environment[WATCHDOG_TOKEN_ENV] = watchdog_token
    environment[WATCHDOG_PID_ENV] = str(os.getpid())
    environment[HEARTBEAT_FILE_ENV] = str(HEARTBEAT_FILE)
    kwargs: dict[str, Any] = {
        "cwd": APP_DIR,
        "env": environment,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    command = _writer_command()
    logger.info("starting PLC width writer: command=%s", command)
    process = subprocess.Popen(command, **kwargs)
    process.watchdog_token = watchdog_token
    return process


def stop_writer_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    logger.warning("stopping unhealthy PLC width writer: pid=%s", process.pid)
    process.terminate()
    try:
        process.wait(timeout=STOP_TIMEOUT)
    except subprocess.TimeoutExpired:
        logger.error(
            "PLC width writer did not stop in %.1fs; killing pid=%s",
            STOP_TIMEOUT,
            process.pid,
        )
        process.kill()
        try:
            process.wait(timeout=STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            logger.critical("PLC width writer remained alive after kill: pid=%s", process.pid)


def supervise_writer_process() -> None:
    process: subprocess.Popen | None = None
    consecutive_failures = 0
    restart_failures = 0
    started_at = 0.0
    try:
        while True:
            if process is None:
                try:
                    process = start_writer_process()
                    started_at = time.monotonic()
                    consecutive_failures = 0
                except Exception as error:
                    restart_failures += 1
                    delay = restart_backoff_seconds(restart_failures)
                    logger.exception(
                        "PLC width writer start failed: attempt=%s retry_in_s=%.1f error=%s",
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
                    "PLC width writer exited: pid=%s exit_code=%s uptime_s=%.1f "
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
            healthy, reason = heartbeat_health(
                process,
                process.watchdog_token,
            )
            if healthy:
                consecutive_failures = 0
                if uptime >= RESTART_STABLE_SECONDS:
                    restart_failures = 0
                continue

            consecutive_failures += 1
            logger.warning(
                "PLC width writer heartbeat failed: pid=%s reason=%s failures=%s/%s",
                process.pid,
                reason,
                consecutive_failures,
                FAILURE_THRESHOLD,
            )
            if consecutive_failures < FAILURE_THRESHOLD:
                continue

            stop_writer_process(process)
            process = None
            consecutive_failures = 0
            restart_failures += 1
            delay = restart_backoff_seconds(restart_failures)
            logger.error(
                "PLC width writer restart scheduled after heartbeat failure: "
                "attempt=%s retry_in_s=%.1f",
                restart_failures,
                delay,
            )
            time.sleep(delay)
    except KeyboardInterrupt:
        logger.info("PLC width writer watchdog shutdown requested")
    finally:
        if process is not None:
            stop_writer_process(process)


def main() -> int:
    configure_logging()
    instance_lock = SingletonLock(
        "plc_width_writer_watchdog",
        pid_dir=APP_DIR / "pids",
    )
    if not instance_lock.acquire():
        logger.error("another PLC width writer watchdog is already running; exiting")
        return 1
    try:
        supervise_writer_process()
        return 0
    finally:
        instance_lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
