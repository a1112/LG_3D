"""Process heartbeat used by the external 3D algorithm watchdog.

The heartbeat deliberately lives outside the algorithm worker threads.  A
native OpenCV/Torch call that never returns can therefore be detected either
because it stops the Python heartbeat thread or because its registered
activity exceeds the configured stall timeout.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parent
SERVICE_NAME = "LG3D_ALGORITHM_3D"
HEARTBEAT_FILE_ENV = "LG3D_ALGORITHM_3D_HEARTBEAT_FILE"
HEARTBEAT_INTERVAL_ENV = "LG3D_ALGORITHM_3D_HEARTBEAT_INTERVAL"
ACTIVITY_TIMEOUT_ENV = "LG3D_ALGORITHM_3D_ACTIVITY_TIMEOUT"
DEFAULT_HEARTBEAT_INTERVAL = 2.0
DEFAULT_ACTIVITY_TIMEOUT = 1800.0


def _positive_float_env(name: str, default: float, minimum: float = 0.1) -> float:
    try:
        return max(float(os.getenv(name, str(default))), minimum)
    except ValueError:
        return default


class RuntimeHeartbeat:
    """Write a small, atomically replaced JSON liveness record."""

    def __init__(self) -> None:
        self.path = Path(
            os.getenv(HEARTBEAT_FILE_ENV, APP_DIR / "log" / "runtime_heartbeat.json")
        )
        self.interval = _positive_float_env(
            HEARTBEAT_INTERVAL_ENV, DEFAULT_HEARTBEAT_INTERVAL
        )
        self.default_activity_timeout = _positive_float_env(
            ACTIVITY_TIMEOUT_ENV, DEFAULT_ACTIVITY_TIMEOUT, minimum=1.0
        )
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._started_at = time.time()
        self._sequence = 0
        self._last_write_at = 0.0
        self._last_write_error = ""
        self._activities: dict[str, dict[str, Any]] = {}

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._started_at = time.time()
            self._thread = threading.Thread(
                target=self._run,
                name="algorithm-3d-heartbeat",
                daemon=True,
            )
            self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=max(float(timeout), 0.0))

    def begin_activity(
        self,
        name: str,
        work_id: Any = None,
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        now = time.time()
        timeout = (
            self.default_activity_timeout
            if timeout_seconds is None
            else max(float(timeout_seconds), 1.0)
        )
        token = uuid.uuid4().hex
        with self._lock:
            self._activities[token] = {
                "name": str(name)[:128],
                "workId": None if work_id is None else str(work_id)[:128],
                "startedAtEpoch": now,
                "progressAtEpoch": now,
                "deadlineAtEpoch": now + timeout,
                "timeoutSeconds": timeout,
                "stage": "started",
            }
        return token

    def progress_activity(self, token: str, stage: str) -> bool:
        now = time.time()
        with self._lock:
            activity = self._activities.get(token)
            if activity is None:
                return False
            activity["progressAtEpoch"] = now
            activity["deadlineAtEpoch"] = now + float(activity["timeoutSeconds"])
            activity["stage"] = str(stage)[:128]
        return True

    def end_activity(self, token: str | None) -> None:
        if token is None:
            return
        with self._lock:
            self._activities.pop(token, None)

    def snapshot(self, now: float | None = None) -> dict[str, Any]:
        now = time.time() if now is None else float(now)
        with self._lock:
            activities = [dict(activity) for activity in self._activities.values()]
            last_write_at = self._last_write_at
            last_write_error = self._last_write_error
            thread_alive = bool(self._thread and self._thread.is_alive())
        overdue = [
            activity
            for activity in activities
            if now > float(activity["deadlineAtEpoch"])
        ]
        return {
            "ok": thread_alive and not overdue,
            "service": SERVICE_NAME,
            "pid": os.getpid(),
            "startedAtEpoch": self._started_at,
            "updatedAtEpoch": last_write_at,
            "heartbeatThreadAlive": thread_alive,
            "activeCount": len(activities),
            "activities": activities,
            "overdueActivities": overdue,
            "lastWriteError": last_write_error,
        }

    def _payload(self, now: float) -> dict[str, Any]:
        with self._lock:
            self._sequence += 1
            sequence = self._sequence
            activities = [dict(activity) for activity in self._activities.values()]
        overdue = [
            activity
            for activity in activities
            if now > float(activity["deadlineAtEpoch"])
        ]
        return {
            "schemaVersion": 1,
            "service": SERVICE_NAME,
            "pid": os.getpid(),
            "sequence": sequence,
            "startedAtEpoch": self._started_at,
            "updatedAtEpoch": now,
            "status": "stalled" if overdue else "ok",
            "activities": activities,
            "overdueActivities": overdue,
        }

    def write_once(self, now: float | None = None) -> bool:
        now = time.time() if now is None else float(now)
        payload = self._payload(now)
        temp_path = self.path.with_name(
            f".{self.path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        )
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            os.replace(temp_path, self.path)
        except OSError as exc:
            with self._lock:
                self._last_write_error = str(exc)[:512]
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            return False
        with self._lock:
            self._last_write_at = now
            self._last_write_error = ""
        return True

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.write_once()
            self._stop_event.wait(self.interval)


runtime_heartbeat = RuntimeHeartbeat()
