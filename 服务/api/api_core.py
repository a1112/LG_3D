import logging

from fastapi import FastAPI
from CONFIG import serverConfigProperty

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
