import logging

from fastapi import FastAPI
from CONFIG import serverConfigProperty
from runtime import runtime_controller

try:
    import orjson
    from fastapi.responses import ORJSONResponse as DefaultResponse
except ImportError:
    from fastapi.responses import JSONResponse as DefaultResponse
    logging.getLogger(__name__).warning("orjson not installed; falling back to JSONResponse")

app = FastAPI(default_response_class=DefaultResponse)

@app.get("/")
async def read_root():
    return {"/docs": "请访问 /docs 查看文档"}

@app.get("/version")
async def read_version():
    return serverConfigProperty.version

@app.get("/delay")
async def get_delay():
    return 0


def _runtime_enabled() -> bool:
    return getattr(app.state, "enable_runtime", True)


@app.on_event("startup")
async def start_runtime_services():
    if _runtime_enabled():
        runtime_controller.start()


@app.on_event("shutdown")
async def stop_runtime_services():
    if _runtime_enabled():
        runtime_controller.stop()
