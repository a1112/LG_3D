import os
import sys
import tempfile
import traceback
from pathlib import Path


def _error_path() -> Path:
    configured = os.getenv("LG3D_MONITOR_DATA_DIR", "").strip()
    root = Path(configured) if configured else (
        Path(tempfile.gettempdir()) / "LG3DServiceMonitor")
    root.mkdir(parents=True, exist_ok=True)
    return root / "startup-error.log"


try:
    from lg3d_service_monitor.application import main

    raise SystemExit(main())
except SystemExit:
    raise
except BaseException:
    _error_path().write_text(traceback.format_exc(), encoding="utf-8")
    raise
