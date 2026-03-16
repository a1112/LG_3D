import json
import logging
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "Base"))
sys.path.append(str(Path(__file__).parent.parent / "algorithm_runtime"))

from fastapi import FastAPI
import uvicorn
from api import app as fastapi_app  # noqa: E402
from Base.CONFIG import configFile  # noqa: E402
from Base.utils.StdoutLog import Logger

Logger("Server")

RUST_IMAGE_SERVICE_HOST = "127.0.0.1"
RUST_IMAGE_SERVICE_PORT = 6013
RUST_IMAGE_SERVICE_URL = f"http://{RUST_IMAGE_SERVICE_HOST}:{RUST_IMAGE_SERVICE_PORT}/health"
RUST_IMAGE_SERVICE_START_TIMEOUT = 8


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _rust_service_healthy() -> bool:
    try:
        with urllib.request.urlopen(RUST_IMAGE_SERVICE_URL, timeout=1.5) as response:
            payload = response.read().decode("utf-8", errors="ignore").strip()
            if response.status != 200:
                return False
            if not payload:
                return True
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                return "ok" in payload.lower() or "healthy" in payload.lower()
            if isinstance(data, dict):
                return True
            return bool(data)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


def _find_rust_image_service_exe() -> Path | None:
    service_dir = Path(__file__).parent / "rust_image_service"
    candidates = [
        service_dir / "target" / "release" / "rust_image_service.exe",
        service_dir / "target" / "release" / "deps" / "rust_image_service.exe",
        service_dir / "target" / "debug" / "rust_image_service.exe",
        service_dir / "target" / "debug" / "deps" / "rust_image_service.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _start_rust_image_service() -> None:
    if not _env_flag("ENABLE_RUST_IMAGE_SERVICE", True):
        logging.info("rust image service autostart disabled by ENABLE_RUST_IMAGE_SERVICE")
        return

    if _rust_service_healthy():
        logging.info("rust image service already healthy on %s", RUST_IMAGE_SERVICE_URL)
        return

    rust_exe = _find_rust_image_service_exe()
    if rust_exe is None:
        logging.warning("rust image service executable not found, skip autostart")
        return

    if _is_port_open(RUST_IMAGE_SERVICE_HOST, RUST_IMAGE_SERVICE_PORT):
        logging.warning(
            "port %s is already in use but rust image service health check failed, skip autostart",
            RUST_IMAGE_SERVICE_PORT,
        )
        return

    command = [
        str(rust_exe),
        "--config",
        str(configFile),
        "--host",
        "0.0.0.0",
        "--port",
        str(RUST_IMAGE_SERVICE_PORT),
    ]

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    try:
        subprocess.Popen(
            command,
            cwd=str(rust_exe.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except Exception as e:
        logging.exception("failed to autostart rust image service: %s", e)
        return

    deadline = time.time() + RUST_IMAGE_SERVICE_START_TIMEOUT
    while time.time() < deadline:
        if _rust_service_healthy():
            logging.info("rust image service started on %s", RUST_IMAGE_SERVICE_URL)
            return
        time.sleep(0.5)

    logging.warning("rust image service did not become healthy within %ss", RUST_IMAGE_SERVICE_START_TIMEOUT)


def _load_default_routers():
    from api import ApiInfo  # noqa: F401
    from api import ApiDataBase  # noqa: F401
    from api import ApiServerControl  # noqa: F401
    from api import ApiDataServer  # noqa: F401
    from api import ApiImageServer  # noqa: F401
    from api import ApiBackupServer  # noqa: F401
    from api import ApiTest  # noqa: F401
    from api import ApiSettings  # noqa: F401
    from AlarmDetection.Server import ApiAlarmInfo  # noqa: F401
    from api import ApiAlgTest  # noqa: F401


def create_app(enable_runtime: bool = True) -> FastAPI:
    _load_default_routers()
    fastapi_app.state.enable_runtime = enable_runtime
    return fastapi_app


def run():
    # 使用 Redis 缓存以支持多进程
    os.environ["IMAGE_CACHE_BACKEND"] = "redis"

    # Windows 不支持多进程 workers，Linux 生产环境可以设置 workers > 1
    workers = 3 if sys.platform == "win32" else 10

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    _start_rust_image_service()

    uvicorn.run(
        "Server:create_app",
        host="0.0.0.0",
        port=5010,
        workers=workers,
        factory=True,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    run()
