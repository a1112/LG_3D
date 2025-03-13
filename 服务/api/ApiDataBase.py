import datetime
import json
from collections import defaultdict

from fastapi import APIRouter

import CONFIG
import Globs
from AlarmDetection import AlarmCoilManagement
from CONFIG import isLoc, serverConfigProperty
from CoilDataBase import Coil, tool
from CoilDataBase.Coil import get_coil_status_by_coil_id, set_coil_status_by_data
from CoilDataBase.models import AlarmInfo, SecondaryCoil, CoilDefect
from property.ServerConfigProperty import ServerConfigProperty
from utils import Hardware, Backup, export
from ._tool_ import get_surface_key
from .api_core import app

serverConfigProperty: ServerConfigProperty

"""
数据库服务

"""
router = APIRouter(tags=["数据库服务"])

def get_coil_item_info(c):
    """
    对Coil数据进行格式化~
    """
    c = tool.to_dict(c)
    if "Weight" in c:
        code = chr(int(c["Weight"]))
        if "Weight" in c:
            c["NextCode"] = code
            try:
                c["NextInfo"] = CONFIG.infoConfigProperty.get_next(str(code))
            except (Exception,) as e:
                print(e)
                c["NextInfo"] = "未知去向，" + str(code)
    return c


def format_secondary_item_data(secondary_coil: SecondaryCoil):
    """
     格式化 单个 二级 返回 数据
     非 自动添加
    """
    c_data = {"hasCoil": False,
              "hasAlarmInfo": False,
              "AlarmInfo" : {},
              "defects": []
              }
    if len(secondary_coil.childrenCoil) > 0:
        c_data["hasCoil"] = True
    for childrenCoil in secondary_coil.childrenCoil:
        c_data.update(get_coil_item_info(childrenCoil))
        if len(secondary_coil.childrenAlarmInfo) > 0:
            c_data["hasAlarmInfo"] = True
        for childrenAlarmInfo in secondary_coil.childrenAlarmInfo:
            childrenAlarmInfo: AlarmInfo
            c_data["AlarmInfo"][childrenAlarmInfo.surface] = get_coil_item_info(childrenAlarmInfo)
        c_data["defects"] = defaultdict(list)
        for childrenCoilDefect in secondary_coil.childrenCoilDefect:
            childrenCoilDefect: CoilDefect
            c_data["defects"][childrenCoilDefect.surface] .append(childrenCoilDefect)
    # del secondary_coil.childrenCoilDefect
    # del secondary_coil.childrenAlarmInfo
    c_data.update(get_coil_item_info(secondary_coil))
    # c_data["defects"] = secondary_coil.childrenCoilDefect

    # c_data["defects"] = secondary_coil.childrenCoilDefect   # 返回缺陷数据
    return c_data

def format_coil_info(secondary_coil_list):
    """
     格式化 二级 返回 数据
    """
    return [format_secondary_item_data(secondary_coil) for secondary_coil in secondary_coil_list]


@router.get("/coilList/{number}")
async def get_coil(number: int,coil_id=None):
    """
        获取 n 条数据
    """
    number= min(number, 1000)
    return format_coil_info(Coil.get_coil_list(number,coil_id, by_coil=isLoc)[::-1])


@router.get("/flush/{coil_id:int}")
async def get_flush(coil_id: int):
    """
    向上刷新
    """
    if coil_id>0:
        return {
            "coilList": await get_coil(10,coil_id=coil_id)
        }
    return {}


@router.get("/search/coilNo/{coil_no:str}")
async def search_by_coil_no(coil_no:str):
    return format_coil_info(Coil.search_by_coil_no(coil_no))


@router.get("/search/coilId/{coil_id}")
async def search_by_coil_id(coil_id: int):
    coil_id = int(coil_id)
    return format_coil_info(Coil.searchByCoilId(coil_id))


@router.get("/search/DateTime/{start:str}/{end:str}")
async def search_by_date_time(start: str, end: str):
    start = datetime.datetime.strptime(start, "%Y%m%d%H%M")
    end = datetime.datetime.strptime(end, "%Y%m%d%H%M")
    return format_coil_info(Coil.searchByDateTime(start, end))


@router.get("/search/CoilState/{coil_id:int}")
async def get_coil_state(coil_id: int):
    coil_id = int(coil_id)
    r = Coil.getCoilState(coil_id)
    return tool.to_dict(r)


@router.get("/search/PlcData/{coil_id:int}")
async def get_plc_data(coil_id: int):
    coil_id = int(coil_id)
    r = Coil.get_plc_data(coil_id)
    return tool.to_dict(r)


@router.get("/search/defects/{coil_id:int}/{direction}")
async def get_defects(coil_id: int, direction: str):
    return tool.to_dict(Coil.get_defects(coil_id, direction))


@router.get("/defectDict")
async def get_defect_dict():
    # return tool.to_dict(Coil.getDefetClassDict())
    return CONFIG.defectClassesProperty.config

@router.get("/defectDictAll")
async def get_defect_dict_all():
    """
    获取全部的表面缺陷数据字段
    """
    return tool.to_dict(Coil.get_defect_class_dict())


@router.get("/coilInfo/{coil_id:int}/{surface_key:str}")
async def get_info(coil_id: int, surface_key: str):
    return serverConfigProperty.get_info(coil_id, surface_key)


async def get_camera_config(coil_id: int, surface_key: str, c):
    return serverConfigProperty.getCameraConfig(coil_id, surface_key)


@router.get("/hardware")
async def get_hardware():
    return Hardware.getHardwareInfo()


@router.get("/cameraAlarm")
async def get_camera_alarm():
    """
      获取相机报警信息
    Returns:
    """
    if CONFIG.isLoc:
        with open("demo/camera_config.json", "r", encoding="utf-8") as f:
            camera_config = json.load(f)
        return {
            "S_D": {
                **camera_config,
                "level": 1,
                "msg": "近端下方相机（右键打开设置）"
            },
            "S_M": {
                **camera_config,
                "level": 1,
                "msg": "近端中间相机（右键打开设置）"
            },
            "S_U": {
                **camera_config,
                "level": 1,
                "msg": "近端上方相机（右键打开设置）"
            },
            "L_D": {
                **camera_config,
                "level": 1,
                "msg": "远端下方相机（右键打开设置）"
            },
            "L_M": {
                **camera_config,
                "level": 1,
                "msg": "远端中间相机（右键打开设置）"
            },
            "L_U": {
                **camera_config,
                "level": 1,
                "msg": "远端上方相机（右键打开设置）"
            },
        }
    else:
        for camera in CONFIG.CameraList:
            camera.getAlarmInfo()


@router.get("/cameraData/{coil_id:int}/{camera_key:str}")
async def get_camera_data(coil_id: int, camera_key: str):
    if CONFIG.isLoc:
        with open("demo/camera_config.json", "r", encoding="utf-8") as f:
            camera_config = json.load(f)
            return camera_config

    return serverConfigProperty.getCameraData(coil_id, camera_key)


@router.get("/coilAlarm/{coil_id:int}")
async def get_coil_alarm(coil_id: int):
    """
    返回全部的警告数据
    Args:
        coil_id:

    Returns:

    """
    return AlarmCoilManagement.get_coil_alarm(coil_id)


@router.get("/backupImageTask/{from_id:int}/{to_id:int}/{save_folder:path}")
async def backup_image_task(from_id: int, to_id: int, save_folder: str):
    print(from_id)
    print(to_id)
    print(save_folder)
    return Backup.backup_image_task(from_id, to_id, save_folder)


@router.get("/get_point_data/{coil_id:int}/{surface_key:str}")
async def get_point_data(coil_id: int, surface_key: str):
    """
    获取点数据
    """
    surface_key = get_surface_key(surface_key)
    return tool.to_dict(Coil.get_point_data(coil_id, surface_key))


@router.get("/get_line_data/{coil_id:int}/{surface_key:str}")
async def get_line_data(coil_id: int, surface_key: str):
    surface_key = get_surface_key(surface_key)
    return tool.to_dict(Coil.get_line_data(coil_id, surface_key))


@router.get("/check/get_coil_status/{coil_id:int}")
async def get_coil_status(coil_id):
    item = tool.to_dict(get_coil_status_by_coil_id(coil_id))
    if not item:
        item = {"status":0,"msg":"","secondaryCoilId":coil_id,"Id":-1}
    return item


@router.get("/check/set_coil_status/{coil_id:int}/{status:int}/{msg:str}")
@router.get("/check/set_coil_status/{coil_id:int}/{status:int}")
async def set_coil_status(coil_id, status, msg=""):
    set_coil_status_by_data(coil_id, status, msg)


app.include_router(router)