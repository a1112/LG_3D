"""
控制系统服务

"""
from typing import Dict

from Globs import control
from .ApiBase import *


@app.get("/control/config")
async def get_config():
    """
    控制配置获取
    """
    return control.getConfig()


@app.post("/control/set_config")
async def set_config(data: Dict):
    """
    控制配置设置
    """
    return control.setConfig(data)


@app.get("/control/set_property")
async def set_property(key,value):
    """
    控制配置设置
    """
    return control.set_property(key, value)
