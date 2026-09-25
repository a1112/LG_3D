import ctypes
import logging
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from Base.utils.watchdog_bootstrap import maybe_exec_watchdog

maybe_exec_watchdog(
    __name__,
    Path(__file__).with_name("watchdog.py"),
    child_environment="LG3D_PLC_WATCHDOG_CHILD",
    disable_environment="LG3D_PLC_DISABLE_AUTO_WATCHDOG",
    service_name="LG3D PLC bridge",
)

import uvicorn

try:
    from . import config
    from .logging_utils import configure_nonblocking_logging
    from .server import PLCError, app, initialize_plc
except ImportError:  # pragma: no cover - direct script/PyInstaller execution
    import config
    from logging_utils import configure_nonblocking_logging
    from server import PLCError, app, initialize_plc


logger = logging.getLogger(__name__)

STD_INPUT_HANDLE = -10
ENABLE_EXTENDED_FLAGS = 0x0080
ENABLE_QUICK_EDIT_MODE = 0x0040


def disable_console_quick_edit() -> bool:
    """Prevent mouse selection from pausing every thread writing the console."""
    if not hasattr(ctypes, "windll"):
        return False
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        mode = ctypes.c_uint32()
        if handle in (0, -1) or not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        new_mode = (mode.value | ENABLE_EXTENDED_FLAGS) & ~ENABLE_QUICK_EDIT_MODE
        return bool(kernel32.SetConsoleMode(handle, new_mode))
    except (AttributeError, OSError, ValueError):
        return False


def main() -> None:
    configure_nonblocking_logging(Path(__file__).resolve().parent / "log" / "plc_server.log")
    disable_console_quick_edit()

    if config.plcForwarderUrl:
        try:
            initialize_plc()
        except PLCError as error:
            # The HTTP service and /health must start even when the PLC is
            # offline. The first operation will make one reconnect attempt.
            logger.warning("initial PLC connection failed; service remains available: %s", error)

    uvicorn.run(
        app=app,
        host=config.server_ip,
        port=config.server_port,
        access_log=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
