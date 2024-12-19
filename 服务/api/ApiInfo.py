
from fastapi import APIRouter

import Init
from Globs import serverConfigProperty
from .api_core import app

router = APIRouter(tags=["参数服务"])


@router.get("/info")
async def info():
    info_ = {
        "ErrorMap": Init.ErrorMap,
        "RendererList": serverConfigProperty.renderer_list,
        "ColorMaps": Init.ColorMaps,
        "SaveImageType": serverConfigProperty.save_image_type,
        "PreviewSize": Init.PreviewSize,
    }
    info_.update(serverConfigProperty.to_dict())
    return info_


app.include_router(router)
