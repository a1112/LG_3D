import asyncio
import json
import math
from queue import Queue
from threading import Thread

from CoilDataBase import Alarm, Coil, tool

from fastapi import APIRouter

from CoilDataBase.models import AlarmFlatRoll

from AlarmDetection.property import alarmConfigProperty
from api.api_core import app


router = APIRouter(tags=["报警、判级"])

def _finite_float(value, default=None):
    try:
        number_value = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return number_value if math.isfinite(number_value) else default


def _positive_float(value, default=None):
    number_value = _finite_float(value, default)
    if number_value is None or number_value <= 0:
        return default
    return number_value


def _parse_json_object(value):
    if isinstance(value, dict):
        return dict(value)
    if not isinstance(value, str) or value == "":
        return {}
    try:
        data = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _coil_state_scale_by_surface(coil_id: int):
    scale_by_surface = {}
    try:
        coil_states = Coil.getCoilState(coil_id)
    except Exception:
        return scale_by_surface
    for coil_state in coil_states or []:
        surface = getattr(coil_state, "surface", None)
        scale = _positive_float(getattr(coil_state, "scan3dCoordinateScaleX", None))
        if surface and scale is not None:
            scale_by_surface[surface] = scale
    return scale_by_surface


def _normalize_loose_alarm_dict(alarm_data: dict, surface_scale=None):
    raw_width = _finite_float(alarm_data.get("max_width"), 0.0) or 0.0
    detail = _parse_json_object(alarm_data.get("data"))
    detail_scale = _positive_float(detail.get("max_width_scale"))
    width_scale = _positive_float(surface_scale, detail_scale or 1.0)
    pixel_width = _finite_float(detail.get("max_width_px"))
    stored_mm = _finite_float(detail.get("max_width_mm"))
    width_unit = str(detail.get("max_width_unit") or "").lower()

    if width_unit == "px":
        pixel_width = pixel_width if pixel_width is not None and pixel_width > 0 else raw_width
        normalized_width = pixel_width * width_scale
    elif stored_mm is not None:
        if pixel_width is not None and pixel_width > 100 and abs(stored_mm - pixel_width) < 0.001:
            normalized_width = pixel_width * width_scale
        else:
            normalized_width = stored_mm
    elif raw_width > 100 and width_scale > 0:
        pixel_width = raw_width
        normalized_width = raw_width * width_scale
    else:
        normalized_width = raw_width

    detail.update({
        "max_width_raw": raw_width,
        "max_width_mm": normalized_width,
        "max_width_unit": "mm",
        "max_width_scale": width_scale,
        "max_width_scale_axis": "x",
    })
    if pixel_width is not None:
        detail["max_width_px"] = pixel_width

    alarm_data["max_width"] = normalized_width
    alarm_data["data"] = json.dumps(detail, ensure_ascii=False)
    return alarm_data


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
    loose_width_scale = _coil_state_scale_by_surface(coil_id)
    alarm_loose = Alarm.getAlarmLooseCoil(coil_id)
    for alarmItem in alarm_loose:
        alarm_data = tool.to_dict(alarmItem)
        surface_scale = loose_width_scale.get(alarmItem.surface)
        LooseCoil[alarmItem.surface].append(_normalize_loose_alarm_dict(alarm_data, surface_scale))
    return {
        "FlatRoll": flat_roll_info,
        "TaperShape": taper_shape_info,
        "LooseCoil": LooseCoil
    }

app.include_router(router)
