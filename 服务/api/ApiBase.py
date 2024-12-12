import CONFIG
import Init
from Globs import serverConfigProperty
from .api_core import app


@app.get("/")
def read_root():
    return {"docs": "请访问 /docs 查看文档"}


@app.get("/version")
def read_version():
    return CONFIG.VERSION


@app.get("/info")
async def info():
    info_ = {
        "ErrorMap": Init.ErrorMap,
        "RendererList": CONFIG.RendererList,
        "ColorMaps": Init.ColorMaps,
        "SaveImageType": CONFIG.SaveImageType,
        "PreviewSize": Init.PreviewSize,
    }
    info_.update(serverConfigProperty.to_dict())
    return info_


@app.get("/delay")
async def getDelay():
    return 0


def getSurfaceKey(surface):
    if "all" == surface:
        return None
    return surface
