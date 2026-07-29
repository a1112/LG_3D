"""Out-of-process liveness signal for the PLC width writer.

The writer touches database and vendor PLC code which cannot always be
interrupted from Python.  A daemon thread therefore publishes both process
liveness and bounded activity deadlines for an external watchdog.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def _runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _runtime_dir()
SERVICE_NAME = "LG3D_PLC_WIDTH_WRITER"
HEARTBEAT_FILE_ENV = "LG3D_PLC_WRITER_HEARTBEAT_FILE"
HEARTBEAT_INTERVAL_ENV = "LG3D_PLC_WRITER_HEARTBEAT_INTERVAL"
ACTIVITY_TIMEOUT_ENV = "LG3D_PLC_WRITER_ACTIVITY_TIMEOUT"
WATCHDOG_TOKEN_ENV = "LG3D_PLC_WRITER_WATCHDOG_TOKEN"
WATCHDOG_PID_ENV = "LG3D_PLC_WRITER_WATCHDOG_PID"
PARENT_CHECK_INTERVAL_ENV = "LG3D_PLC_WRITER_PARENT_CHECK_INTERVAL"
DEFAULT_HEARTBEAT_INTERVAL = 2.0
DEFAULT_ACTIVITY_TIMEOUT = 60.0


def _positive_float_env(name: str, default: float, minimum: float) -> float:
    try:
        return max(float(os.getenv(name, str(default))), minimum)
    except (TypeError, ValueError):
        return default


class PlcWriterHeartbeat:
    """Atomically publish liveness and potentially blocked operations."""

    def __init__(self) -> None:
        self.path = Path(
            os.getenv(
                HEARTBEAT_FILE_ENV,
                str(APP_DIR / "log" / "plc_writer_heartbeat.json"),
            )
        )
        self.interval = _positive_float_env(
            HEARTBEAT_INTERVAL_ENV,
            DEFAULT_HEARTBEAT_INTERVAL,
            0.1,
        )
        self.default_activity_timeout = _positive_float_env(
            ACTIVITY_TIMEOUT_ENV,
            DEFAULT_ACTIVITY_TIMEOUT,
            1.0,
        )
        self.watchdog_token = os.getenv(WATCHDOG_TOKEN_ENV, "")[:128]
        try:
            parent_pid = int(os.getenv(WATCHDOG_PID_ENV, "0"))
        except (TypeError, ValueError):
            parent_pid = 0
        self.watchdog_pid = parent_pid if parent_pid > 0 else None
        self.parent_check_interval = _positive_float_env(
            PARENT_CHECK_INTERVAL_ENV,
            DEFAULT_HEARTBEAT_INTERVAL,
            0.1,
        )
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._guardian_thread: threading.Thread | None = None
        self._started_at = time.time()
        self._sequence = 0
        self._activities: dict[str, dict[str, Any]] = {}

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._started_at = time.time()
            # Publish immediately so a slow database/vendor import is still
            # distinguishable from a child which never reached Python code.
            self.write_once()
            self._thread = threading.Thread(
                target=self._run,
                name="plc-writer-heartbeat",
                daemon=True,
            )
            self._thread.start()
            if self.watchdog_pid is not None:
                self._guardian_thread = threading.Thread(
                    target=self._guard_parent,
                    name="plc-writer-parent-guardian",
                    daemon=True,
                )
                self._guardian_thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=max(float(timeout), 0.0))
        guardian = self._guardian_thread
        if guardian is not None and guardian is not threading.current_thread():
            guardian.join(timeout=max(float(timeout), 0.0))

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
                "deadlineAtEpoch": now + timeout,
                "timeoutSeconds": timeout,
            }
        return token

    def end_activity(self, token: str | None) -> None:
        if token is None:
            return
        with self._lock:
            self._activities.pop(token, None)

    @contextmanager
    def activity(
        self,
        name: str,
        work_id: Any = None,
        *,
        timeout_seconds: float | None = None,
    ) -> Iterator[None]:
        token = self.begin_activity(
            name,
            work_id,
            timeout_seconds=timeout_seconds,
        )
        try:
            yield
        finally:
            self.end_activity(token)

    def _payload(self, now: float) -> dict[str, Any]:
        with self._lock:
            self._sequence += 1
            sequence = self._sequence
            activities = [dict(value) for value in self._activities.values()]
        overdue = [
            value
            for value in activities
            if now > float(value["deadlineAtEpoch"])
        ]
        return {
            "schemaVersion": 1,
            "service": SERVICE_NAME,
            "pid": os.getpid(),
            "watchdogToken": self.watchdog_token,
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
            return True
        except OSError:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval):
            self.write_once()

    @staticmethod
    def _process_alive(pid: int) -> bool:
        if sys.platform == "win32":
            import ctypes

            synchronize = 0x00100000
            wait_timeout = 0x00000102
            kernel32 = ctypes.windll.kernel32
            kernel32.OpenProcess.argtypes = (
                ctypes.c_uint32,
                ctypes.c_bool,
                ctypes.c_uint32,
            )
            kernel32.OpenProcess.restype = ctypes.c_void_p
            kernel32.WaitForSingleObject.argtypes = (
                ctypes.c_void_p,
                ctypes.c_uint32,
            )
            kernel32.WaitForSingleObject.restype = ctypes.c_uint32
            kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
            kernel32.CloseHandle.restype = ctypes.c_bool
            handle = kernel32.OpenProcess(synchronize, False, int(pid))
            if not handle:
                return False
            try:
                return kernel32.WaitForSingleObject(handle, 0) == wait_timeout
            finally:
                kernel32.CloseHandle(handle)
        try:
            os.kill(int(pid), 0)
            return True
        except PermissionError:
            return True
        except OSError:
            return False

    def _guard_parent(self) -> None:
        while not self._stop_event.wait(self.parent_check_interval):
            if self.watchdog_pid is None or self._process_alive(self.watchdog_pid):
                continue
            # Avoid leaving an unmonitored orphan which would keep the writer
            # singleton locked and prevent a replacement watchdog from taking
            # control. os._exit is intentional: the main thread may be stuck
            # inside an uninterruptible vendor call.
            os._exit(70)


writer_heartbeat = PlcWriterHeartbeat()
