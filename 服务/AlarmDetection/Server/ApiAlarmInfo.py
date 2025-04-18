import asyncio
import json
from queue import Queue
from threading import Thread

from CoilDataBase import Alarm, tool

from CoilDataBase.Coil import get_coil_status_by_coil_id

from fastapi import APIRouter
from fastapi import WebSocket

import CONFIG
import Globs
from CoilDataBase.models import AlarmFlatRoll
from api.api_core import app
from CONFIG import alarmConfigProperty


router = APIRouter(tags=["报警、判级"])

@router.get("/coilAlarm/get_info")
async def get_info():
    """
    获取报警信息
    Returns:
    """
    return alarmConfigProperty.get_info_json()


@router.get("/coilAlarm/{coil_id:int}")
async def get_coil_alarm(coil_id: int):
    """
    返回全部的警告数据
    Args:
        coil_id:

    Returns:
    """

    flat_roll_info = {}
    alarm_flat_roll_list = Alarm.getAlarmFlatRoll(coil_id)
    for alarmItem in alarm_flat_roll_list[::-1]:
        alarmItem: AlarmFlatRoll
        flat_roll_info[alarmItem.surface] = tool.to_dict(alarmItem)

    taper_shape_info = {
        "S": [],
        "L": []
    }

    alarm_taper_shape_list = Alarm.getAlarmTaperShape(coil_id)
    for alarmItem in alarm_taper_shape_list:
        taper_shape_info[alarmItem.surface].append(tool.to_dict(alarmItem))

    LooseCoil = {
        "L": [],
        "S": []
    }
    alarm_loose = Alarm.getAlarmLooseCoil(coil_id)
    for alarmItem in alarm_loose:
        LooseCoil[alarmItem.surface].append(tool.to_dict(alarmItem))
    return {
        "FlatRoll": flat_roll_info,
        "TaperShape": taper_shape_info,
        "LooseCoil": LooseCoil
    }

app.include_router(router)