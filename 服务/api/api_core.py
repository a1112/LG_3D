from fastapi import FastAPI

from Globs import serverConfigProperty

app = FastAPI()

@app.get("/")
def read_root():
    return {"/docs": "请访问 /docs 查看文档"}

@app.get("/version")
def read_version():
    return serverConfigProperty.version

@app.get("/delay")
async def get_delay():
    return 0