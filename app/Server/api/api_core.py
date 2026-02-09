import logging
import time

from fastapi import FastAPI
from cache import get_cache_mode, shutdown_cache, startup_cache

try:
    import orjson
    from fastapi.responses import ORJSONResponse as DefaultResponse
except ImportError:
    from fastapi.responses import JSONResponse as DefaultResponse
    logging.getLogger(__name__).warning("orjson not installed; falling back to JSONResponse")

app = FastAPI(default_response_class=DefaultResponse)


@app.middleware("http")
async def performance_middleware(request, call_next):
    """性能监控中间件：追踪 API 响应时间"""
    start_time = time.perf_counter()

    # 只监控图像 API
    if "/image/" in request.url.path:
        response = await call_next(request)
        process_time = time.perf_counter() - start_time

        # 记录慢请求
        if process_time > 0.1:  # 100ms
            logging.warning("[PERF] SLOW: %s took %.3fs", request.url.path, process_time)
        elif process_time > 0.05:  # 50ms
            logging.info("[PERF] %s took %.3fs", request.url.path, process_time)

        response.headers["X-Process-Time"] = str(process_time)
        return response

    return await call_next(request)

@app.on_event("startup")
def _startup_cache() -> None:
    startup_cache()


@app.on_event("shutdown")
def _shutdown_cache() -> None:
    shutdown_cache()

@app.get("/")
async def read_root():
    return {"/docs": "请访问 /docs 查看文档"}

@app.get("/version")
async def read_version():
    return "0.1.1"

@app.get("/delay")
async def get_delay():
    return 0


def _runtime_enabled() -> bool:
    return getattr(app.state, "enable_runtime", True)


