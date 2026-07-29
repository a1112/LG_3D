import logging
import os
import runpy
import sys
from pathlib import Path


_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in _TRUE_VALUES


def maybe_exec_watchdog(
    entrypoint_name: str,
    watchdog_path: Path,
    *,
    child_environment: str,
    disable_environment: str,
    service_name: str,
) -> bool:
    """Replace a directly launched source service with its watchdog.

    Watchdogs mark the real child process through ``child_environment``. This
    lets existing production launchers keep invoking the historical service
    script without creating a recursive watchdog chain. Frozen executables are
    left unchanged because their source-side watchdog may not be bundled.
    """
    if entrypoint_name != "__main__" or getattr(sys, "frozen", False):
        return False
    if (_env_enabled(child_environment)
            or _env_enabled(disable_environment)
            or _env_enabled("LG3D_DISABLE_AUTO_WATCHDOG")):
        return False

    resolved_watchdog = Path(watchdog_path).resolve()
    if not resolved_watchdog.is_file():
        logging.getLogger(__name__).error(
            "%s watchdog is missing; continue without supervision: %s",
            service_name,
            resolved_watchdog,
        )
        return False

    if sys.platform == "win32":
        # Windows' execv implementation does not preserve the launcher process
        # lifetime like POSIX exec. Running in-process keeps the calling
        # .bat/cmd alive, which is how the external UI monitor determines that
        # a source launcher is still running. Once started, fail closed so the
        # outer monitor can retry instead of silently running unsupervised.
        runpy.run_path(str(resolved_watchdog), run_name="__main__")
        raise SystemExit(0)

    try:
        os.execv(sys.executable, [sys.executable, str(resolved_watchdog)])
    except OSError as error:
        logging.getLogger(__name__).exception(
            "%s watchdog bootstrap failed; continue without supervision: %s",
            service_name,
            error,
        )
        return False
    return True
