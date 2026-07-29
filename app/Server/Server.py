import atexit
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

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(APP_ROOT))
sys.path.append(str(APP_ROOT / "Base"))
sys.path.append(str(APP_ROOT / "algorithm_runtime"))

from Base.utils.watchdog_bootstrap import maybe_exec_watchdog  # noqa: E402

maybe_exec_watchdog(
    __name__,
    Path(__file__).with_name("watchdog.py"),
    child_environment="LG3D_API_WATCHDOG_CHILD",
    disable_environment="LG3D_API_DISABLE_AUTO_WATCHDOG",
    service_name="LG3D API",
)

from fastapi import FastAPI
import uvicorn
from runtime_settings import ensure_default_cache_backend, get_api_workers  # noqa: E402
from Base.utils.nonblocking_logging import configure_nonblocking_logging  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_LOG_DIR = Path(os.getenv("LG3D_LOG_DIR", PROJECT_ROOT / "log")) / "Server"
logging_runtime = configure_nonblocking_logging(
    API_LOG_DIR / f"Server_{os.getpid()}.log",
    root_level=logging.DEBUG,
    file_level=logging.DEBUG,
    console_level=logging.INFO,
)

ensure_default_cache_backend()

from api import app as fastapi_app  # noqa: E402
from Base.CONFIG import configFile  # noqa: E402
from Base.utils.StdoutLog import Logger

Logger("Server")

RUST_IMAGE_SERVICE_HOST = "127.0.0.1"
RUST_IMAGE_SERVICE_PORT = 6013
RUST_IMAGE_SERVICE_URL = f"http://{RUST_IMAGE_SERVICE_HOST}:{RUST_IMAGE_SERVICE_PORT}/health"
RUST_IMAGE_SERVICE_START_TIMEOUT = 8
RUST_IMAGE_SERVICE_MIN_API_VERSION = 2
RUST_API_SERVICE_HOST = "127.0.0.1"
RUST_API_SERVICE_PORT = 5011
RUST_API_SERVICE_URL = f"http://{RUST_API_SERVICE_HOST}:{RUST_API_SERVICE_PORT}/health"
RUST_API_SERVICE_START_TIMEOUT = 12
_managed_rust_processes: list[subprocess.Popen] = []


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


def _rust_service_healthy(service_url: str,
                          expected_service: str,
                          minimum_api_version: int | None = None) -> bool:
    try:
        with urllib.request.urlopen(service_url, timeout=1.5) as response:
            payload = response.read().decode("utf-8", errors="ignore").strip()
            if response.status != 200:
                return False
            if not payload:
                return minimum_api_version is None
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                if minimum_api_version is not None:
                    logging.debug(
                        "rust service %s health response has no apiVersion",
                        expected_service)
                    return False
                return "ok" in payload.lower() or "healthy" in payload.lower()
            if isinstance(data, dict):
                if data.get("service") != expected_service or data.get(
                        "status") != "ok":
                    return False
                if minimum_api_version is None:
                    return True

                api_version = data.get("apiVersion")
                try:
                    api_version = int(api_version)
                except (TypeError, ValueError):
                    logging.debug(
                        "rust service %s health response has invalid apiVersion=%r",
                        expected_service, api_version)
                    return False
                if api_version < minimum_api_version:
                    logging.debug(
                        "rust service %s apiVersion=%s is older than required=%s",
                        expected_service, api_version, minimum_api_version)
                    return False
                return True
            if minimum_api_version is not None:
                return False
            return bool(data)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


def _find_rust_service_exe(service_name: str) -> Path | None:
    service_dir = Path(__file__).parent / service_name
    candidates = [
        service_dir / "target" / "release" / f"{service_name}_v2.exe",
        service_dir / "target" / "release" / f"{service_name}.exe",
        service_dir / "target" / "release" / "deps" / f"{service_name}.exe",
        service_dir / "target" / "debug" / f"{service_name}.exe",
        service_dir / "target" / "debug" / "deps" / f"{service_name}.exe",
    ]
    existing_candidates = []
    for order, candidate in enumerate(candidates):
        try:
            modified_ns = candidate.stat().st_mtime_ns
        except OSError:
            continue
        existing_candidates.append((modified_ns, -order, candidate))

    if not existing_candidates:
        return None

    modified_ns, _, selected = max(existing_candidates)
    logging.info(
        "selected newest rust service executable service=%s path=%s modified_ns=%s",
        service_name, selected, modified_ns)
    return selected


def _register_rust_process(process: subprocess.Popen) -> None:
    _managed_rust_processes.append(process)


def _stop_managed_rust_services() -> None:
    while _managed_rust_processes:
        process = _managed_rust_processes.pop()
        if process.poll() is not None:
            continue
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception as e:
            logging.warning("failed to stop managed rust service pid=%s: %s",
                            process.pid, e)


atexit.register(_stop_managed_rust_services)


def _start_rust_image_service() -> None:
    if not _env_flag("ENABLE_RUST_IMAGE_SERVICE", True):
        logging.info(
            "rust image service autostart disabled by ENABLE_RUST_IMAGE_SERVICE"
        )
        return

    if _rust_service_healthy(RUST_IMAGE_SERVICE_URL, "rust_image_service",
                             RUST_IMAGE_SERVICE_MIN_API_VERSION):
        logging.info("rust image service already healthy on %s",
                     RUST_IMAGE_SERVICE_URL)
        return

    rust_exe = _find_rust_service_exe("rust_image_service")
    if rust_exe is None:
        logging.warning(
            "rust image service executable not found, skip autostart")
        return

    if _is_port_open(RUST_IMAGE_SERVICE_HOST, RUST_IMAGE_SERVICE_PORT):
        logging.warning(
            "port %s is already in use but rust image service health check failed "
            "(required apiVersion >= %s), skip autostart",
            RUST_IMAGE_SERVICE_PORT,
            RUST_IMAGE_SERVICE_MIN_API_VERSION,
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
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW

    try:
        process = subprocess.Popen(
            command,
            cwd=str(rust_exe.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except Exception as e:
        logging.exception("failed to autostart rust image service: %s", e)
        return

    _register_rust_process(process)

    deadline = time.time() + RUST_IMAGE_SERVICE_START_TIMEOUT
    while time.time() < deadline:
        if _rust_service_healthy(RUST_IMAGE_SERVICE_URL, "rust_image_service",
                                 RUST_IMAGE_SERVICE_MIN_API_VERSION):
            logging.info("rust image service started on %s",
                         RUST_IMAGE_SERVICE_URL)
            return
        time.sleep(0.5)

    logging.warning("rust image service did not become healthy within %ss",
                    RUST_IMAGE_SERVICE_START_TIMEOUT)


def _rust_api_environment() -> dict[str, str] | None:
    environment = os.environ.copy()
    database_url = environment.get("COIL_DATABASE_URL")

    if not database_url:
        try:
            from CoilDataBase.config import get_url

            database_url = get_url()
        except Exception as e:
            logging.warning(
                "unable to resolve database URL for rust API service: %s", e)
            return None

    supported_schemes = (
        "mysql://",
        "mysql+",
        "postgres://",
        "postgres+",
        "postgresql://",
        "postgresql+",
    )
    if not database_url.lower().startswith(supported_schemes):
        logging.warning(
            "rust API service requires a MySQL or PostgreSQL database URL; skip autostart"
        )
        return None

    environment["COIL_DATABASE_URL"] = database_url
    return environment


def _start_rust_api_service() -> None:
    if not _env_flag("ENABLE_RUST_API_SERVICE", True):
        logging.info(
            "rust API service autostart disabled by ENABLE_RUST_API_SERVICE")
        return

    if _rust_service_healthy(RUST_API_SERVICE_URL, "rust_api_service"):
        logging.info("rust API service already healthy on %s",
                     RUST_API_SERVICE_URL)
        return

    rust_exe = _find_rust_service_exe("rust_api_service")
    if rust_exe is None:
        logging.warning(
            "rust API service executable not found, skip autostart")
        return

    if _is_port_open(RUST_API_SERVICE_HOST, RUST_API_SERVICE_PORT):
        logging.warning(
            "port %s is already in use but rust API service health check failed, skip autostart",
            RUST_API_SERVICE_PORT,
        )
        return

    environment = _rust_api_environment()
    if environment is None:
        return

    command = [
        str(rust_exe),
        "--host",
        "0.0.0.0",
        "--port",
        str(RUST_API_SERVICE_PORT),
    ]
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    try:
        process = subprocess.Popen(
            command,
            cwd=str(rust_exe.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=environment,
            creationflags=creationflags,
        )
    except Exception as e:
        logging.exception("failed to autostart rust API service: %s", e)
        return

    _register_rust_process(process)
    deadline = time.time() + RUST_API_SERVICE_START_TIMEOUT
    while time.time() < deadline:
        if _rust_service_healthy(RUST_API_SERVICE_URL, "rust_api_service"):
            logging.info("rust API service started on %s",
                         RUST_API_SERVICE_URL)
            return
        if process.poll() is not None:
            break
        time.sleep(0.5)

    logging.warning("rust API service did not become healthy within %ss",
                    RUST_API_SERVICE_START_TIMEOUT)


def _load_default_routers(enable_runtime: bool = True):
    from api import ApiInfo  # noqa: F401
    from api import ApiDataBase  # noqa: F401
    from api import ApiServerControl  # noqa: F401
    from api import ApiDataServer  # noqa: F401
    from api import ApiImageServer  # noqa: F401
    from api import ApiCompat  # noqa: F401
    from api import ApiBackupServer  # noqa: F401
    from api import ApiTest  # noqa: F401
    from api import ApiSettings  # noqa: F401
    from AlarmDetection.Server import ApiAlarmInfo  # noqa: F401
    from api import ApiAlgTest  # noqa: F401
    from api import ApiTool  # noqa: F401
    if enable_runtime:
        from api import ApiServer  # noqa: F401


def create_app(enable_runtime: bool = True) -> FastAPI:
    fastapi_app.state.enable_runtime = enable_runtime
    _load_default_routers(enable_runtime=enable_runtime)
    return fastapi_app


def run():
    # 默认单进程；需要水平扩展时通过 API_WORKERS 显式配置，并同步评估 DB 连接池容量。
    workers = get_api_workers(sys.platform)

    _start_rust_api_service()
    _start_rust_image_service()

    try:
        uvicorn.run(
            "Server:create_app",
            host="0.0.0.0",
            port=5010,
            workers=workers,
            factory=True,
            log_level="info",
            access_log=True,
            log_config=None,
        )
    finally:
        _stop_managed_rust_services()


if __name__ == "__main__":
    run()
