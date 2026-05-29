from __future__ import annotations

import os
import shutil
import shlex
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _set_qt_environment(base_dir: Path) -> None:
    # Some deployments (services/sandboxed users) can't write to the default
    # Windows profile directories. Provide a writable fallback inside the app.
    try:
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            probe = Path(local_appdata) / "LG_3D" / "MotionStudio" / "cache" / "_probe"
            probe.mkdir(parents=True, exist_ok=True)
        else:
            raise OSError("LOCALAPPDATA not set")
    except Exception:
        appdata_root = base_dir / "py" / "_appdata"
        (appdata_root / "Local").mkdir(parents=True, exist_ok=True)
        (appdata_root / "Roaming").mkdir(parents=True, exist_ok=True)
        os.environ["LOCALAPPDATA"] = str(appdata_root / "Local")
        os.environ["APPDATA"] = str(appdata_root / "Roaming")

    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qml.connections=false")
    conf = base_dir / "qtquickcontrols2.conf"
    if conf.exists():
        os.environ.setdefault("QT_QUICK_CONTROLS_CONF", str(conf))

    cache_dir = base_dir / "py" / "_cache"
    (cache_dir / "qml").mkdir(parents=True, exist_ok=True)
    (cache_dir / "rhi").mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("QML_DISK_CACHE_PATH", str(cache_dir / "qml"))
    os.environ.setdefault("QSG_RHI_SHADER_CACHE_DIR", str(cache_dir / "rhi"))


def _ensure_rcc(*, base_dir: Path, qrc_filename: str) -> Path:
    qrc_path = base_dir / qrc_filename
    if not qrc_path.exists():
        raise FileNotFoundError(str(qrc_path))

    out_dir = base_dir / "py" / "_rcc"
    out_dir.mkdir(parents=True, exist_ok=True)
    rcc_path = out_dir / f"{qrc_path.stem}.rcc"

    latest_source_mtime = qrc_path.stat().st_mtime
    try:
        tree = ET.parse(qrc_path)
        for file_node in tree.iter("file"):
            if not file_node.text:
                continue
            source_path = qrc_path.parent / file_node.text
            if source_path.exists():
                latest_source_mtime = max(latest_source_mtime, source_path.stat().st_mtime)
    except Exception:
        latest_source_mtime = qrc_path.stat().st_mtime

    if rcc_path.exists():
        try:
            with open(rcc_path, "rb") as f:
                head = f.read(64)
            looks_like_python = head.startswith(b"#") and b"Resource object code" in head
        except Exception:
            looks_like_python = False

        if (not looks_like_python) and rcc_path.stat().st_mtime >= latest_source_mtime:
            return rcc_path

    pyside_rcc = shutil.which("pyside6-rcc")
    if not pyside_rcc:
        py_exe_dir = Path(sys.executable).resolve().parent
        candidates = [
            py_exe_dir / "pyside6-rcc.exe",
            py_exe_dir / "pyside6-rcc",
            py_exe_dir / "Scripts" / "pyside6-rcc.exe",
            py_exe_dir / "Scripts" / "pyside6-rcc",
        ]
        for c in candidates:
            if c.exists():
                pyside_rcc = str(c)
                break
    if not pyside_rcc:
        raise RuntimeError("Cannot find `pyside6-rcc` on PATH or near the Python executable.")

    subprocess.run(
        [pyside_rcc, str(qrc_path), "--binary", "-o", str(rcc_path)],
        cwd=str(base_dir),
        check=True,
    )
    return rcc_path


class ScriptLauncher:  # QObject subclass is created lazily after Qt import
    pass


class FileDownloader:  # QObject subclass is created lazily after Qt import
    pass


class ClipboardController:  # QObject subclass is created lazily after Qt import
    pass


class ConsoleController:  # QObject subclass is created lazily after Qt import
    pass


@dataclass(frozen=True)
class _DownloadTask:
    url: str
    save_path: str
    payload: Optional[str] = None


def run(*, base_dir: Path) -> int:
    _set_qt_environment(base_dir)

    try:
        from PySide6.QtCore import (
            QCoreApplication,
            QObject,
            Property,
            QResource,
            QUrl,
            Signal,
            Slot,
        )
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
        from PySide6.QtWidgets import QApplication
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing Qt bindings. Install `PySide6` to run MotionStudio QML UI."
        ) from exc

    class _ScriptLauncher(QObject):
        def _path_from_url_or_path(self, value: str) -> Path:
            if value.startswith("file:"):
                url = QUrl(value)
                return Path(url.toLocalFile())
            norm = value
            if os.name == "nt":
                norm = norm.replace("/", "\\")
            return Path(norm)

        @Slot(str, result=bool)
        def fileExists(self, path: str) -> bool:
            return self._path_from_url_or_path(path).exists()

        @Slot(result=bool)
        def developerMode(self) -> bool:
            return os.getenv("API_DEVELOPER_MODE", "").lower() in {"1", "true", "yes", "on"}

        def _ensure_testdata_mesh(self, surface_key: str, coil_id: str) -> Optional[Path]:
            try:
                project_root = base_dir.parents[2]
                server_dir = project_root / "app" / "Server"
                if str(server_dir) not in sys.path:
                    sys.path.insert(0, str(server_dir))
                from testdata_mesh import ensure_testdata_mesh

                return ensure_testdata_mesh(surface_key, coil_id)
            except Exception as exc:
                print(f"Failed to prepare testdata mesh {surface_key}/{coil_id}: {exc}", file=sys.stderr)
                return None

        @Slot(str, str, result=str)
        def testDataMeshPath(self, surface_key: str, coil_id: str) -> str:
            path = self._ensure_testdata_mesh(surface_key, coil_id)
            return "" if path is None else str(path)

        @Slot(str, str, result=str)
        def testDataMeshUrl(self, surface_key: str, coil_id: str) -> str:
            path = self._ensure_testdata_mesh(surface_key, coil_id)
            return "" if path is None else QUrl.fromLocalFile(str(path)).toString()

        @Slot(str, str, result=bool)
        def testDataMeshExists(self, surface_key: str, coil_id: str) -> bool:
            path = self._ensure_testdata_mesh(surface_key, coil_id)
            return path is not None and path.exists()

        @Slot(str, result=bool)
        def launchScript(self, cmd_args: str) -> bool:
            if os.name != "nt":
                return False
            try:
                subprocess.Popen(
                    ["cmd.exe", *shlex.split(cmd_args, posix=False)],
                    cwd=str(base_dir),
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                return True
            except Exception:
                return False

    class _FileDownloader(QObject):
        downloadProgress = Signal(int, int)
        downloadFinished = Signal()
        downloadError = Signal(str)

        @Slot(str, str, result=bool)
        @Slot(str, str, str, result=bool)
        def downloadFile(self, url: str, save_path: str, payload: str = "") -> bool:
            task = _DownloadTask(url=url, save_path=save_path, payload=payload or None)
            threading.Thread(target=self._do_download, args=(task,), daemon=True).start()
            return True

        def _do_download(self, task: _DownloadTask) -> None:
            try:
                import requests

                save_path = Path(task.save_path)
                save_path.parent.mkdir(parents=True, exist_ok=True)

                if task.payload is None:
                    resp = requests.get(task.url, stream=True, timeout=60)
                else:
                    resp = requests.post(
                        task.url,
                        data=task.payload.encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        stream=True,
                        timeout=60,
                    )
                resp.raise_for_status()

                total = int(resp.headers.get("Content-Length") or 0)
                received = 0
                with open(save_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 128):
                        if not chunk:
                            continue
                        f.write(chunk)
                        received += len(chunk)
                        self.downloadProgress.emit(received, total)
                self.downloadFinished.emit()
            except Exception as exc:
                self.downloadError.emit(str(exc))

    class _ClipboardController(QObject):
        @Slot(str)
        def setText(self, text: str) -> None:
            cb = QGuiApplication.clipboard()
            if cb is not None:
                cb.setText(text)

        @Slot(result=str)
        def text(self) -> str:
            cb = QGuiApplication.clipboard()
            return "" if cb is None else cb.text()

    class _ConsoleController(QObject):
        isShowChanged = Signal()

        def __init__(self) -> None:
            super().__init__()
            self._is_show = True

        def _get_is_show(self) -> bool:
            return self._is_show

        def _set_is_show(self, value: bool) -> None:
            if self._is_show == value:
                return
            self._is_show = value
            self.isShowChanged.emit()

        isShow = Property(bool, _get_is_show, _set_is_show, notify=isShowChanged)

    ScriptLauncher = _ScriptLauncher
    FileDownloader = _FileDownloader
    ClipboardController = _ClipboardController
    ConsoleController = _ConsoleController

    qmlRegisterType(ClipboardController, "Clipboard", 1, 0, "Clipboard")
    qmlRegisterType(ConsoleController, "ConsoleController", 1, 0, "ConsoleController")

    QCoreApplication.setOrganizationName("LG_3D")
    QCoreApplication.setOrganizationDomain("local")
    QCoreApplication.setApplicationName("MotionStudio")

    os.chdir(base_dir)
    app = QApplication([])
    engine = QQmlApplicationEngine()

    def _print_warnings(warnings) -> None:
        for w in warnings:
            try:
                print(w.toString(), file=sys.stderr)
            except Exception:
                print(str(w), file=sys.stderr)

    try:
        engine.warnings.connect(_print_warnings)  # type: ignore[attr-defined]
    except Exception:
        pass

    engine.rootContext().setContextProperty("ScriptLauncher", ScriptLauncher())
    engine.rootContext().setContextProperty("fileDownloader", FileDownloader())

    qml_rcc = _ensure_rcc(base_dir=base_dir, qrc_filename="qml.qrc")
    res_rcc = _ensure_rcc(base_dir=base_dir, qrc_filename="resource.qrc")
    if not QResource.registerResource(str(qml_rcc)):
        raise RuntimeError(f"Failed to register resource: {qml_rcc}")
    if not QResource.registerResource(str(res_rcc)):
        raise RuntimeError(f"Failed to register resource: {res_rcc}")

    engine.addImportPath(":/")
    engine.addImportPath("qrc:/")

    entry_qml = QUrl("qrc:/qml/App.qml")
    engine.load(entry_qml)

    if not engine.rootObjects():
        print(f"Failed to load QML: {entry_qml.toString()}", file=sys.stderr)
        print(f"Import paths: {engine.importPathList()}", file=sys.stderr)
        return 1
    return app.exec()
