import logging
import os
import sys
import time
from pathlib import Path

APP_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from Base.utils.watchdog_bootstrap import maybe_exec_watchdog


WATCHDOG_CHILD_ENV = "LG3D_PLC_WRITER_WATCHDOG_CHILD"
WATCHDOG_DISABLE_ENV = "LG3D_PLC_WRITER_DISABLE_AUTO_WATCHDOG"

maybe_exec_watchdog(
    __name__,
    Path(__file__).with_name("write_plc_watchdog.py"),
    child_environment=WATCHDOG_CHILD_ENV,
    disable_environment=WATCHDOG_DISABLE_ENV,
    service_name="LG3D PLC width writer",
)


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


# A frozen writer contains the watchdog module and supervises another copy of
# its own executable. Source launches are handled by maybe_exec_watchdog().
if (
    __name__ == "__main__"
    and getattr(sys, "frozen", False)
    and not _env_enabled(WATCHDOG_CHILD_ENV)
    and not _env_enabled(WATCHDOG_DISABLE_ENV)
    and not _env_enabled("LG3D_DISABLE_AUTO_WATCHDOG")
):
    try:
        from .write_plc_watchdog import main as watchdog_main
    except ImportError:  # pragma: no cover - PyInstaller direct entrypoint
        from write_plc_watchdog import main as watchdog_main

    raise SystemExit(watchdog_main())

_runtime_instance_lock = None
if __name__ == "__main__":
    from Base.utils.Singleton import SingletonLock

    _runtime_instance_lock = SingletonLock(
        "plc_width_writer",
        pid_dir=APP_DIR / "pids",
    )
    if not _runtime_instance_lock.acquire():
        logging.getLogger(__name__).error(
            "another PLC width writer is already running; exiting"
        )
        raise SystemExit(1)

try:
    from .plc_writer_heartbeat import writer_heartbeat
except ImportError:  # pragma: no cover - direct script/PyInstaller execution
    from plc_writer_heartbeat import writer_heartbeat

_startup_activity_token = None
if __name__ == "__main__":
    writer_heartbeat.start()
    _startup_activity_token = writer_heartbeat.begin_activity("runtime_imports")

try:
    import requests

    from CoilDataBase.Coil import addToPlc, get_coil_by_coil_no

    try:
        from .logging_utils import configure_nonblocking_logging
        from .server import read_plc, write_plc
    except ImportError:  # pragma: no cover - direct script/PyInstaller execution
        from logging_utils import configure_nonblocking_logging
        from server import read_plc, write_plc
finally:
    writer_heartbeat.end_activity(_startup_activity_token)

logger = logging.getLogger(__name__)

CURRENT_COIL_URL = "http://127.0.0.1:6005/currentCoil"
PLC_WIDTH_ADDR = "DB35.40"
POLL_INTERVAL_SECONDS = 3
RETRY_INTERVAL_SECONDS = 5


def _read_plc(addr: str, type_str: str, length: int):
    with writer_heartbeat.activity("plc_read", addr):
        return read_plc(addr, type_str, length)


def _write_plc(addr: str, type_str: str, value):
    with writer_heartbeat.activity("plc_write", addr):
        return write_plc(addr, type_str, value)


def add_plc(coil_no) -> None:
    if not coil_no:
        return
    with writer_heartbeat.activity("database_read_previous_coil", coil_no):
        coil = get_coil_by_coil_no(coil_no)
    if coil is None:
        return
    plc_snapshot = {
        "secondaryCoilId": coil.Id,
        "location_S": _read_plc("M34", "real", 4),
        "location_L": _read_plc("M38", "real", 4),
        "location_laser": _read_plc("DB35.340", "int", 4),
    }
    with writer_heartbeat.activity("database_write_plc_snapshot", coil_no):
        addToPlc(plc_snapshot)


def get_current_coil() -> dict:
    with writer_heartbeat.activity("current_coil_http_request"):
        response = requests.get(CURRENT_COIL_URL, timeout=3)
        response.raise_for_status()
        data = response.json()
    if not isinstance(data, dict):
        raise ValueError(f"currentCoil 响应不是字典: {data}")
    return data


def get_act_w(data: dict):
    for key in ("act_w", "ActWidth", "ACT_W", "width", "Width"):
        value = data.get(key)
        if value is not None:
            return int(value)
    return None


def poll_once(old_id):
    data = get_current_coil()
    coil_id = data.get("Coil_ID")
    act_w = get_act_w(data)

    if coil_id is None or act_w is None:
        logger.warning("currentCoil missing required fields: %s", data)
        return old_id

    old_w = _read_plc(PLC_WIDTH_ADDR, "int", 2)

    if old_id != coil_id:
        logger.info("new coil detected: %s", coil_id)
        try:
            add_plc(old_id)
        except Exception as e:
            logger.warning(
                "add previous coil PLC snapshot failed: coil_id=%s error=%s",
                old_id,
                e,
            )
        old_id = coil_id

    if old_w != act_w:
        _write_plc(PLC_WIDTH_ADDR, "int", act_w)
        logger.info("wrote PLC width %s=%s for coil=%s", PLC_WIDTH_ADDR, act_w, coil_id)
        logger.debug("currentCoil payload: %s", data)
    return old_id


def main() -> int:
    try:
        configure_nonblocking_logging(APP_DIR / "log" / "write_plc.log")
        old_id = ""
        while True:
            try:
                with writer_heartbeat.activity("poll_cycle", old_id):
                    old_id = poll_once(old_id)
                time.sleep(POLL_INTERVAL_SECONDS)
            except Exception as e:
                logger.warning("PLC write or currentCoil fetch failed: %s", e)
                time.sleep(RETRY_INTERVAL_SECONDS)
    finally:
        writer_heartbeat.stop()
        if _runtime_instance_lock is not None:
            _runtime_instance_lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
