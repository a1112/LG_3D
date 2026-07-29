import asyncio
from contextlib import asynccontextmanager
import logging
import os
import time

from fastapi import FastAPI
from cache import shutdown_cache, startup_cache
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import MutableHeaders

try:
    import orjson
    from fastapi.responses import ORJSONResponse as DefaultResponse
except ImportError:
    from fastapi.responses import JSONResponse as DefaultResponse
    logging.getLogger(__name__).warning("orjson not installed; falling back to JSONResponse")

def _positive_float_env(name: str, default: float) -> float:
    try:
        return max(float(os.getenv(name, str(default))), 0.1)
    except ValueError:
        logging.getLogger(__name__).warning("invalid %s, use default %s", name,
                                            default)
        return default


def _positive_int_env(name: str, default: int) -> int:
    try:
        return max(int(os.getenv(name, str(default))), 1)
    except ValueError:
        logging.getLogger(__name__).warning("invalid %s, use default %s", name,
                                            default)
        return default


_THREADPOOL_CANARY_INTERVAL = _positive_float_env(
    "API_THREADPOOL_CANARY_INTERVAL", 5.0)
_THREADPOOL_CANARY_TIMEOUT = _positive_float_env(
    "API_THREADPOOL_CANARY_TIMEOUT", 2.0)
_THREADPOOL_CANARY_FAILURE_THRESHOLD = _positive_int_env(
    "API_THREADPOOL_CANARY_FAILURE_THRESHOLD", 3)
_THREADPOOL_CANARY_STALE_SECONDS = _positive_float_env(
    "API_THREADPOOL_CANARY_STALE_SECONDS", 30.0)


async def _run_threadpool_canary_probe(state: dict) -> None:
    started_at = time.monotonic()
    try:
        await asyncio.wait_for(run_in_threadpool(lambda: None),
                               timeout=_THREADPOOL_CANARY_TIMEOUT)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        state["consecutiveFailures"] = int(
            state.get("consecutiveFailures", 0)) + 1
        state["lastError"] = type(exc).__name__
    else:
        state["consecutiveFailures"] = 0
        state["lastSuccessMonotonic"] = time.monotonic()
        state["lastError"] = ""
    finally:
        state["lastProbeDuration"] = round(time.monotonic() - started_at, 3)


async def _threadpool_canary_loop(state: dict) -> None:
    while True:
        await _run_threadpool_canary_probe(state)
        await asyncio.sleep(_THREADPOOL_CANARY_INTERVAL)


@asynccontextmanager
async def lifespan(_app):
    startup_cache()
    state = {
        "consecutiveFailures": 0,
        "lastSuccessMonotonic": time.monotonic(),
        "lastProbeDuration": 0.0,
        "lastError": "",
    }
    _app.state.threadpool_canary = state
    canary_task = asyncio.create_task(_threadpool_canary_loop(state),
                                      name="api-threadpool-canary")
    try:
        yield
    finally:
        canary_task.cancel()
        await asyncio.gather(canary_task, return_exceptions=True)
        shutdown_cache()


class ImagePerformanceMiddleware:
    """Track image response setup time without BaseHTTPMiddleware overhead."""

    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or "/image/" not in scope["path"]:
            await self.application(scope, receive, send)
            return

        started = time.perf_counter()

        async def send_with_timing(message):
            if message["type"] == "http.response.start":
                process_time = time.perf_counter() - started
                if process_time > 0.1:
                    logging.warning("[PERF] SLOW: %s took %.3fs", scope["path"],
                                    process_time)
                elif process_time > 0.05:
                    logging.info("[PERF] %s took %.3fs", scope["path"],
                                 process_time)
                MutableHeaders(scope=message)["X-Process-Time"] = str(
                    process_time)
            await send(message)

        await self.application(scope, receive, send_with_timing)


app = FastAPI(default_response_class=DefaultResponse, lifespan=lifespan)
app.add_middleware(ImagePerformanceMiddleware)

@app.get("/")
async def read_root():
    return {"/docs": "请访问 /docs 查看文档"}


@app.get("/health")
async def health():
    # Keep this endpoint independent from the database, Redis, capture service
    # and camera SDK. It verifies that this process can still schedule work on
    # the ASGI event loop.
    payload = {
        "ok": True,
        "service": "LG3D_API",
        "time": time.time(),
    }
    unhealthy = False
    image_health_probe = getattr(app.state, "image_operation_health", None)
    if callable(image_health_probe):
        try:
            image_health = image_health_probe()
        except Exception as exc:
            logging.exception("image executor health probe failed: %s", exc)
            image_health = {"ok": False, "error": type(exc).__name__}
        payload["imageExecutor"] = image_health
        if image_health.get("ok") is not True:
            unhealthy = True

    render_health_probe = getattr(app.state, "render_operation_health", None)
    if callable(render_health_probe):
        try:
            render_health = render_health_probe()
        except Exception as exc:
            logging.exception("render executor health probe failed: %s", exc)
            render_health = {"ok": False, "error": type(exc).__name__}
        payload["renderExecutor"] = render_health
        if render_health.get("ok") is not True:
            unhealthy = True

    threadpool_state = getattr(app.state, "threadpool_canary", None)
    if isinstance(threadpool_state, dict):
        success_age = max(
            time.monotonic() - float(
                threadpool_state.get("lastSuccessMonotonic", 0.0)), 0.0)
        threadpool_health = {
            "ok": (
                int(threadpool_state.get("consecutiveFailures", 0))
                < _THREADPOOL_CANARY_FAILURE_THRESHOLD
                and success_age < _THREADPOOL_CANARY_STALE_SECONDS),
            "consecutiveFailures": int(
                threadpool_state.get("consecutiveFailures", 0)),
            "lastSuccessAge": round(success_age, 3),
            "lastProbeDuration": threadpool_state.get("lastProbeDuration",
                                                        0.0),
            "lastError": threadpool_state.get("lastError", ""),
        }
        payload["threadpool"] = threadpool_health
        if threadpool_health["ok"] is not True:
            unhealthy = True

    if unhealthy:
        payload["ok"] = False
        return DefaultResponse(payload, status_code=503)
    return payload


@app.get("/version")
async def read_version():
    return "0.1.1"

@app.get("/delay")
async def get_delay():
    return 0


def _runtime_enabled() -> bool:
    return getattr(app.state, "enable_runtime", True)


