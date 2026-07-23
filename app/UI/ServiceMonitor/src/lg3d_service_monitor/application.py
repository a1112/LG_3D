import argparse
import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from lg3d_service_monitor import __version__
from lg3d_service_monitor.config.paths import (
    ENV_DATA_DIR,
    ENV_LG3D_ROOT,
    ENV_READ_ONLY,
    data_root,
    ensure_runtime_directories,
    launcher_directory,
    lg3d_root,
    pid_file,
    resources_root,
)
from lg3d_service_monitor.config.service_registry import load_service_registry
from lg3d_service_monitor.monitoring.disk import DiskMonitor
from lg3d_service_monitor.monitoring.path_info import PathInfo
from lg3d_service_monitor.monitoring.process import ProcessObj
from lg3d_service_monitor.monitoring.services import SoftMonitor
from lg3d_service_monitor.platform.windows.clipboard import Clipboard
from lg3d_service_monitor.platform.windows.icons import IconImageProvider
from lg3d_service_monitor.platform.windows.software import SoftList


MUTEX_NAME = "Local\\LG3DServiceMonitor"
ERROR_ALREADY_EXISTS = 183


class AlreadyRunningError(RuntimeError):
    pass


class OS(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._os = sys.platform

    @Slot(str)
    def system(self, cmd):
        try:
            subprocess.Popen(str(cmd), shell=False, close_fds=True)
        except OSError:
            os.startfile(str(cmd))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="LG3DServiceMonitor")
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="validate packaged resources and runtime paths, then exit",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="observe services without starting, stopping, or restarting them",
    )
    parser.add_argument(
        "--lg3d-root",
        help="explicit LG_3D root; preferred when crossing a Windows UAC boundary",
    )
    parser.add_argument(
        "--data-dir",
        help="explicit writable configuration and log directory",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def acquire_instance_mutex():
    if os.name != "nt":
        return None
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_bool,
        ctypes.c_wchar_p,
    ]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_bool
    kernel32.SetLastError(0)
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        raise OSError("CreateMutexW failed")
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        raise AlreadyRunningError("LG3DServiceMonitor is already running")
    return handle


def release_instance_mutex(handle) -> None:
    if handle and os.name == "nt":
        ctypes.windll.kernel32.CloseHandle(handle)


def self_check() -> dict:
    registry = load_service_registry()
    qml_file = resources_root() / "main.qml"
    if not qml_file.is_file():
        raise FileNotFoundError(f"QML entrypoint not found: {qml_file}")
    missing_launchers = [
        service["launcher"]
        for service in registry["services"]
        if not (launcher_directory() / service["launcher"]).is_file()
    ]
    if missing_launchers:
        raise FileNotFoundError(
            "missing service launchers: " + ", ".join(missing_launchers))
    ensure_runtime_directories()
    probe = data_root() / ".write-test"
    probe.write_text(str(time.time()), encoding="utf-8")
    probe.unlink()
    return {
        "ok": True,
        "version": __version__,
        "lg3dRoot": str(lg3d_root()),
        "dataRoot": str(data_root()),
        "qml": str(qml_file),
        "launcherDirectory": str(launcher_directory()),
        "serviceCount": len(registry["services"]),
    }


def _record_self_check(payload: dict) -> None:
    targets = [
        Path(tempfile.gettempdir()) / "LG3DServiceMonitor-self-check.json",
    ]
    try:
        targets.append(data_root() / "self-check.json")
    except Exception:
        pass
    for target in targets:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            continue


def _write_pid_record() -> None:
    target = pid_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "executable": str(Path(sys.executable).resolve()),
                "startedAt": time.time(),
                "version": __version__,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _remove_pid_record() -> None:
    target = pid_file()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        if int(payload.get("pid", 0)) == os.getpid():
            target.unlink(missing_ok=True)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass


def _record_qml_warnings(warnings) -> None:
    try:
        target = data_root() / "logs" / "Application" / "qml-errors.log"
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as stream:
            for warning in warnings:
                stream.write(warning.toString() + "\n")
    except OSError:
        pass


def run_gui(read_only: bool = False) -> int:
    if read_only:
        os.environ[ENV_READ_ONLY] = "1"
    ensure_runtime_directories()
    mutex = acquire_instance_mutex()
    try:
        _write_pid_record()
        app = QGuiApplication(sys.argv[:1])
        app.setApplicationName("LG3DServiceMonitor")
        app.setOrganizationName("LG_3D")
        qmlRegisterType(ProcessObj, "ProcessObj", 1, 0, "ProcessObj")
        qmlRegisterType(SoftList, "SoftList", 1, 0, "SoftList")
        qmlRegisterType(SoftMonitor, "SoftMonitor", 1, 0, "SoftMonitor")
        qmlRegisterType(DiskMonitor, "DiskMonitor", 1, 0, "DiskMonitor")
        qmlRegisterType(PathInfo, "DiskMonitor", 1, 0, "PathInfo")
        qmlRegisterType(Clipboard, "Clipboard", 1, 0, "Clipboard")

        engine = QQmlApplicationEngine()
        engine.warnings.connect(_record_qml_warnings)
        engine.addImageProvider("icon", IconImageProvider())
        engine.rootContext().setContextProperty("Os", OS())
        engine.load(resources_root() / "main.qml")
        if not engine.rootObjects():
            return 2
        return app.exec()
    finally:
        _remove_pid_record()
        release_instance_mutex(mutex)


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if args.lg3d_root:
        os.environ[ENV_LG3D_ROOT] = args.lg3d_root
    if args.data_dir:
        os.environ[ENV_DATA_DIR] = args.data_dir
    if args.self_check:
        try:
            result = self_check()
            _record_self_check(result)
            print(json.dumps(result, ensure_ascii=False))
            return 0
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
            _record_self_check(result)
            print(
                json.dumps(result, ensure_ascii=False),
                file=sys.stderr,
            )
            return 1
    try:
        return run_gui(read_only=args.read_only)
    except AlreadyRunningError as exc:
        print(str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
