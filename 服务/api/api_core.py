from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from CONFIG import serverConfigProperty

app = FastAPI(default_response_class=ORJSONResponse)

@app.get("/")
async def read_root():
    return {"/docs": "请访问 /docs 查看文档"}

@app.get("/version")
async def read_version():
    return serverConfigProperty.version

@app.get("/delay")
async def get_delay():
    return 0