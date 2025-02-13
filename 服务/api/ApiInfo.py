
from fastapi import APIRouter

import Init
from CONFIG import serverConfigProperty, defectClassesProperty
from .api_core import app
from CoilDataBase.core import engine
from CoilDataBase.Coil import get_coil, list_data_keys
from CoilDataBase.tool import to_dict


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

# @router.get("/defectClasses")
# async def get_defect_classes():
#     return defectClassesProperty.config




@router.get("/database_info")
async def database_info():
    """
    获取数据库信息
    """
    coil_last = None
    try:
        coil_last = to_dict(get_coil(1)[0])
    except (BaseException,) as e:
        print(e)
    return {
        "url":engine.url,
        "echo":engine.echo,
        "coil_last":coil_last
    }

@router.get("/coil_list_value_change_keys")
async def coil_list_value_change_keys():

    return list(list_data_keys.keys())


app.include_router(router)