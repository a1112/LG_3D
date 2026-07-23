# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path


project_root = Path(
    os.getenv("LG3D_MONITOR_PROJECT_ROOT", Path(SPECPATH).resolve().parent)
).resolve()
lg3d_root = project_root.parents[2]
source_root = project_root / "src"
diagnostic = os.getenv("LG3D_MONITOR_DIAGNOSTIC", "") == "1"
executable_name = (
    "LG3DServiceMonitor-debug" if diagnostic else "LG3DServiceMonitor")

a = Analysis(
    [str(project_root / "packaging" / "entrypoint.py")],
    pathex=[str(source_root)],
    binaries=[],
    datas=[
        (str(project_root / "resources"), "resources"),
        (str(project_root / "config" / "defaults"), "config/defaults"),
        (
            str(
                lg3d_root
                / "CONFIG_3D"
                / "service_monitor"
                / "services.json"
            ),
            "config/defaults",
        ),
    ],
    hiddenimports=["win32api", "win32gui"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=executable_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=diagnostic,
    uac_admin=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(project_root / "resources" / "app.ico")],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=executable_name,
)
