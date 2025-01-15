"""
控制系统服务

"""
from typing import Dict

from fastapi import APIRouter

from Globs import control
from .api_core import app

router = APIRouter(tags=["参数控制服务"])

@router.get("/control/config")
async def get_config():
    """
    控制配置获取
    """
    return control.get_config()


@router.post("/control/set_config")
async def set_config(data: Dict):
    """
    控制配置设置
    """
    return control.set_config(data)


@router.get("/control/set_property")
async def set_property(key,value):
    """
    控制配置设置
    """
    return control.set_property(key, value)

app.include_router(router)