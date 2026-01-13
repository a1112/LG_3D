import logging

from fastapi import FastAPI
from cache import get_cache_mode, shutdown_cache, startup_cache

try:
    import orjson
    from fastapi.responses import ORJSONResponse as DefaultResponse
except ImportError:
    from fastapi.responses import JSONResponse as DefaultResponse
    logging.getLogger(__name__).warning("orjson not installed; falling back to JSONResponse")

app = FastAPI(default_response_class=DefaultResponse)

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


