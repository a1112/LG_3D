import asyncio
import datetime
import math
import json
import logging
import os
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException
from PIL import Image
from pydantic import BaseModel
from sqlalchemy import func
from starlette.concurrency import run_in_threadpool

from Base import CONFIG
from Base.CONFIG import isLoc, serverConfigProperty
from CoilDataBase import Coil, tool
from CoilDataBase.core import Session
from CoilDataBase.Coil import get_coil_status_by_coil_id, set_coil_status_by_data
from CoilDataBase.CoilSummary import (
    batch_sync_summaries,
    get_coil_detail,
    get_coil_list_hybrid,
    get_coil_list_with_summary,
    search_coils_by_coil_no_summary,
    search_coils_by_datetime_summary,
    search_coils_by_id_summary,
)
from CoilDataBase.models import (AlarmInfo, AlarmFlatRoll, AlarmLooseCoil,
                                AlarmTaperShape, CoilDefect, CoilState,
                                PlcData, SecondaryCoil)
from Base.property.ServerConfigProperty import ServerConfigProperty
from Base.utils import Hardware, Backup, export
from ._tool_ import get_surface_key
from .api_core import app
from .hardware_monitor import (control_network_adapter,
                               get_network_adapters,
                               get_service_statuses, restart_service)
from testdata_config import get_testdata_coil_id, get_testdata_coil_info, get_testdata_dir

serverConfigProperty: ServerConfigProperty
"""
数据库服务

"""
router = APIRouter(tags=["数据库服务"])

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CAMERA_SERVICE_TIMEOUT = 1.5
_CAPTURE_MONITOR_TIMEOUT = 4.0
logger = logging.getLogger(__name__)


class CameraAdjustmentPayload(BaseModel):
    exposureTime: Optional[int] = None
    gain: Optional[int] = None
    save: bool = True


class NetworkAdapterControlPayload(BaseModel):
    action: str


def _test_mode_enabled() -> bool:
    if os.getenv("API_DEVELOPER_MODE", "").lower() in {"1", "true", "yes", "on"}:
        return True
    if _test_mode_config_enabled():
        return True
    return bool(getattr(CONFIG, "developer_mode", False) and getattr(CONFIG, "isLoc", False))


def _test_mode_config_enabled() -> bool:
    try:
        test_mode_config_path = Path(CONFIG.base_config_folder) / "test_mode_config.json"
        if test_mode_config_path.exists():
            config = json.loads(test_mode_config_path.read_text(encoding="utf-8"))
            if bool(config.get("test_mode", False)):
                return True
    except Exception as e:
        logger.debug("test mode config read failed: %s", e)
    return False


def _testdata_available() -> bool:
    base = get_testdata_dir()
    if not base.exists():
        return False
    if (base / "3D.npz").exists():
        return True
    return any((base / surface / "3D.npz").exists() for surface in ("S", "L"))


def _test_mode_coil_item() -> dict:
    testdata_coil_id = int(get_testdata_coil_id())
    testdata_dir = get_testdata_dir()
    try:
        testdata_msg = str(testdata_dir.relative_to(_PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        testdata_msg = str(testdata_dir)
    now = datetime.datetime.now()
    date_value = {
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "weekday": now.weekday(),
        "hour": now.hour,
        "minute": now.minute,
        "second": now.second,
    }
    alarm_info = {
        surface: {
            "surface": surface,
            "grad": 1,
            "defectGrad": 1,
            "taperShapeGrad": 1,
            "looseCoilGrad": 1,
            "flatRollGrad": 1,
            "defectMsg": "",
            "taperShapeMsg": "测试模式",
            "looseCoilMsg": "",
            "flatRollMsg": "测试模式",
        }
        for surface in ("S", "L")
    }
    return {
        "Id": testdata_coil_id,
        "SecondaryCoilId": testdata_coil_id,
        "CoilNo": str(testdata_coil_id),
        "CoilType": "TestData",
        "CoilInside": "",
        "CoilDia": "",
        "Thickness": "",
        "Width": "",
        "Weight": "",
        "ActWidth": "",
        "CheckStatus": 0,
        "DefectCountS": 0,
        "DefectCountL": 0,
        "Status_L": 0,
        "Status_S": 0,
        "Grade": 0,
        "Msg": testdata_msg,
        "NextInfo": "测试模式",
        "NextCode": "",
        "hasCoil": True,
        "hasAlarmInfo": True,
        "AlarmInfo": alarm_info,
        "defects": {},
        "childrenCoilCheck": [],
        "CreateTime": date_value,
        "DetectionTime": date_value,
        "DateTime": date_value,
    }


def _with_test_mode_coil_fallback(data):
    if not (_test_mode_enabled() and _testdata_available()):
        return data

    test_item = _test_mode_coil_item()
    if isinstance(data, dict):
        values = data.get("value")
        if isinstance(values, list):
            fallback = dict(data)
            fallback["value"] = [test_item]
            fallback["Count"] = max(int(fallback.get("Count") or 0), 1)
            return fallback
    elif isinstance(data, list):
        return [test_item]
    return data

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
            except (Exception, ) as e:
                logger.debug("failed to resolve next info: code=%s error=%s", code, e)
                c["NextInfo"] = "未知去向，" + str(code)
    return c


def format_secondary_item_data(secondary_coil: SecondaryCoil):
    """
     格式化 单个 Communication 返回 数据
     非 自动添加
    """
    c_data = {
        "hasCoil": False,
        "hasAlarmInfo": False,
        "AlarmInfo": {},
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
            c_data["AlarmInfo"][
                childrenAlarmInfo.surface] = get_coil_item_info(
                    childrenAlarmInfo)
        c_data["defects"] = defaultdict(list)
        for childrenCoilDefect in secondary_coil.childrenCoilDefect:
            childrenCoilDefect: CoilDefect
            c_data["defects"][childrenCoilDefect.surface].append(
                childrenCoilDefect)
    # del secondary_coil.childrenCoilDefect
    # del secondary_coil.childrenAlarmInfo
    c_data.update(get_coil_item_info(secondary_coil))
    # c_data["defects"] = secondary_coil.childrenCoilDefect

    # c_data["defects"] = secondary_coil.childrenCoilDefect   # 返回缺陷数据
    return c_data


def format_coil_info(secondary_coil_list):
    """
     格式化 Communication 返回 数据
    """
    return [
        format_secondary_item_data(secondary_coil)
        for secondary_coil in secondary_coil_list
    ]


def _parse_json_string(value: object) -> dict:
    if not isinstance(value, str):
        return {}
    try:
        data = json.loads(value)
    except Exception:
        return {}
    if isinstance(data, dict):
        return data
    return {}


def _to_finite_float(value: object) -> Optional[float]:
    if isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            return float(value)
    return None


def _scale_from_state(state_rows):
    scale_by_surface = {}
    for row in state_rows:
        surface = row.surface
        if surface not in {"S", "L"}:
            continue
        if surface in scale_by_surface:
            continue
        scale = _to_finite_float(row.scan3dCoordinateScaleX)
        if scale is not None and scale > 0:
            scale_by_surface[surface] = scale
    return scale_by_surface


def _round_numeric_value(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 6)


def _normalize_loose_coil_entry(item: dict, scale: Optional[float]) -> dict:
    item = dict(item)
    raw_width = _to_finite_float(item.get("max_width")) or 0.0
    detail = _parse_json_string(item.get("data"))
    detail_width_unit = str(detail.get("max_width_unit") or "").lower()

    parsed_pixel = _to_finite_float(detail.get("max_width_px"))
    parsed_mm = _to_finite_float(detail.get("max_width_mm"))
    detail_scale = _to_finite_float(detail.get("max_width_scale"))
    width_scale = scale if scale and scale > 0 else detail_scale
    if width_scale is None or width_scale <= 0:
        width_scale = 1.0

    if detail_width_unit == "px":
        pixel_width = parsed_pixel if parsed_pixel and parsed_pixel > 0 else raw_width
        normalized_width = pixel_width * width_scale
        if pixel_width > 0:
            detail["max_width_px"] = _round_numeric_value(pixel_width)
    elif parsed_mm is not None:
        if parsed_pixel is not None and parsed_pixel > 100 and abs(parsed_mm - parsed_pixel) < 0.001:
            normalized_width = parsed_pixel * width_scale
        else:
            normalized_width = parsed_mm
    elif raw_width > 100 and width_scale > 0:
        pixel_width = raw_width
        normalized_width = raw_width * width_scale
        detail["max_width_px"] = _round_numeric_value(pixel_width)
    else:
        normalized_width = raw_width

    normalized_width = _round_numeric_value(normalized_width or 0)
    item["max_width"] = normalized_width
    item["data"] = json.dumps({
        **detail,
        "max_width_raw": _round_numeric_value(raw_width),
        "max_width_mm": normalized_width,
        "max_width_unit": "mm",
        "max_width_scale": _round_numeric_value(width_scale),
        "max_width_scale_axis": "x",
    }, ensure_ascii=False)
    return item


def _load_coil_alarm_payload(coil_id: int) -> dict:
    with Session() as session:
        flat_roll_rows = session.query(AlarmFlatRoll).filter_by(
            secondaryCoilId=coil_id).order_by(AlarmFlatRoll.Id.desc()).all()
        taper_rows = session.query(AlarmTaperShape).filter_by(
            secondaryCoilId=coil_id).all()
        loose_rows = session.query(AlarmLooseCoil).filter_by(
            secondaryCoilId=coil_id).all()
        state_rows = session.query(CoilState).filter(
            CoilState.secondaryCoilId == coil_id,
            CoilState.surface.in_(["S", "L"]),
        ).order_by(CoilState.Id.desc()).all()

    scale_by_surface = _scale_from_state(state_rows)

    payload = {
        "FlatRoll": {"S": {}, "L": {}},
        "TaperShape": {"S": [], "L": []},
        "LooseCoil": {"S": [], "L": []},
    }

    for row in flat_roll_rows:
        row_dict = tool.to_dict(row)
        surface = row.surface
        if surface in {"S", "L"} and not payload["FlatRoll"][surface]:
            payload["FlatRoll"][surface] = row_dict

    for row in taper_rows:
        row_dict = tool.to_dict(row)
        surface = row.surface
        if surface in {"S", "L"}:
            payload["TaperShape"][surface].append(row_dict)

    for row in loose_rows:
        row_dict = tool.to_dict(row)
        surface = row.surface
        if surface in {"S", "L"}:
            row_dict = _normalize_loose_coil_entry(
                row_dict,
                scale_by_surface.get(surface),
            )
            payload["LooseCoil"][surface].append(row_dict)

    return payload


@router.get("/coilList/{number}")
async def get_coil(number: int, coil_id=None, rev=True):
    """
    获取 n 条数据（优先查询摘要表，快速返回）

    摘要表由算法检测结束时自动更新，确保数据一致性
    """
    number = min(number, 1000)
    # 直接查询摘要表，不进行同步（快速返回）
    data = get_coil_list_with_summary(
        limit=number,
        coil_id=coil_id,
        rev=rev,
        by_coil=isLoc,
        auto_sync=False
    )
    return _with_test_mode_coil_fallback(data)


@router.get("/flush/{coil_id:int}")
async def get_flush(coil_id: int):
    """
    向上刷新（仅查询摘要表，快速返回）
    """
    if coil_id > 0:
        return {
            "coilList":
            get_coil_list_with_summary(limit=10,
                                       coil_id=coil_id,
                                       rev=True,
                                       by_coil=isLoc)
        }
    return {}


@router.get("/search/coilNo/{coil_no:str}")
async def search_by_coil_no(coil_no: str):
    return search_coils_by_coil_no_summary(coil_no, by_coil=True)


@router.get("/search/coilId/{coil_id}")
async def search_by_coil_id(coil_id: int):
    coil_id = int(coil_id)
    return search_coils_by_id_summary(coil_id, by_coil=True)


@router.get("/search/DateTime/{start:str}/{end:str}")
async def search_by_date_time(start: str, end: str):
    start = datetime.datetime.strptime(start, "%Y%m%d%H%M")
    end = datetime.datetime.strptime(end, "%Y%m%d%H%M")
    return search_coils_by_datetime_summary(start, end, by_coil=True)


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


def _query_plc_curve_rows(start_id: int = 0,
                          end_id: int = 0,
                          limit: int = 200):
    limit = min(max(int(limit), 1), 2000)
    if start_id and end_id and start_id > end_id:
        start_id, end_id = end_id, start_id

    order_desc = not start_id and not end_id

    with Session() as session:
        base_query = session.query(PlcData.secondaryCoilId,
                                   func.max(PlcData.Id).label("max_id"))
        if start_id:
            base_query = base_query.filter(PlcData.secondaryCoilId >= start_id)
        if end_id:
            base_query = base_query.filter(PlcData.secondaryCoilId <= end_id)
        base_query = base_query.group_by(PlcData.secondaryCoilId).subquery()

        query = session.query(PlcData).join(base_query,
                                            PlcData.Id == base_query.c.max_id)
        if order_desc:
            query = query.order_by(PlcData.secondaryCoilId.desc())
        else:
            query = query.order_by(PlcData.secondaryCoilId.asc())
        query = query.limit(limit)
        rows = query.all()

    if order_desc:
        rows = list(reversed(rows))
    return rows


@router.get("/plc_curve/{field}")
async def get_plc_curve(field: str,
                        start_id: int = 0,
                        end_id: int = 0,
                        limit: int = 200):
    field_map = {
        "location_S": PlcData.location_S,
        "location_L": PlcData.location_L,
        "location_laser": PlcData.location_laser,
    }
    if field not in field_map:
        return {"field": field, "items": [], "error": "invalid field"}

    rows = _query_plc_curve_rows(start_id, end_id, limit)
    items = []
    for row in rows:
        items.append({
            "coil_id": row.secondaryCoilId,
            "time": row.startTime.isoformat() if row.startTime else "",
            "value": getattr(row, field),
        })
    return {"field": field, "items": items}

    limit = min(max(int(limit), 1), 2000)
    if start_id and end_id and start_id > end_id:
        start_id, end_id = end_id, start_id

    order_desc = not start_id and not end_id

    with Session() as session:
        base_query = session.query(PlcData.secondaryCoilId,
                                   func.max(PlcData.Id).label("max_id"))
        if start_id:
            base_query = base_query.filter(PlcData.secondaryCoilId >= start_id)
        if end_id:
            base_query = base_query.filter(PlcData.secondaryCoilId <= end_id)
        base_query = base_query.group_by(PlcData.secondaryCoilId).subquery()

        query = session.query(PlcData).join(base_query,
                                            PlcData.Id == base_query.c.max_id)
        if order_desc:
            query = query.order_by(PlcData.secondaryCoilId.desc())
        else:
            query = query.order_by(PlcData.secondaryCoilId.asc())
        query = query.limit(limit)
        rows = query.all()

    if order_desc:
        rows = list(reversed(rows))

    items = []
    for row in rows:
        items.append({
            "coil_id": row.secondaryCoilId,
            "time": row.startTime.isoformat() if row.startTime else "",
            "value": getattr(row, field),
        })
    return {"field": field, "items": items}


@router.get("/plc_curve_all")
async def get_plc_curve_all(start_id: int = 0,
                            end_id: int = 0,
                            limit: int = 200):
    rows = _query_plc_curve_rows(start_id, end_id, limit)
    coil_ids = [row.secondaryCoilId for row in rows]
    state_map = {}
    width_map = {}
    if coil_ids:
        with Session() as session:
            state_sub = session.query(
                CoilState.secondaryCoilId.label("coil_id"),
                CoilState.surface.label("surface"),
                func.max(CoilState.Id).label("max_id")).filter(
                    CoilState.secondaryCoilId.in_(coil_ids),
                    CoilState.surface.in_(["S", "L"])).group_by(
                        CoilState.secondaryCoilId,
                        CoilState.surface).subquery()
            state_rows = session.query(CoilState).join(
                state_sub, CoilState.Id == state_sub.c.max_id).all()
            width_rows = session.query(
                SecondaryCoil.Id, SecondaryCoil.ActWidth).filter(
                    SecondaryCoil.Id.in_(coil_ids)).all()
        for state in state_rows:
            state_map[(state.secondaryCoilId,
                       state.surface)] = state.median_3d_mm
        for row in width_rows:
            width_map[row[0]] = row[1]

    items = []
    for row in rows:
        s_mm = state_map.get((row.secondaryCoilId, "S"))
        l_mm = state_map.get((row.secondaryCoilId, "L"))
        avg_mm = None
        if s_mm is not None and l_mm is not None:
            avg_mm = (s_mm + l_mm) / 2
        items.append({
            "coil_id": row.secondaryCoilId,
            "time": row.startTime.isoformat() if row.startTime else "",
            "location_S": row.location_S,
            "location_L": row.location_L,
            "location_laser": row.location_laser,
            "median_3d_mm_S": s_mm,
            "median_3d_mm_L": l_mm,
            "median_3d_mm_avg": avg_mm,
            "width_": width_map.get(row.secondaryCoilId),
        })
    return {"items": items}


@router.get("/search/defects/{coil_id:int}/{direction}")
async def get_defects(coil_id: int, direction: str):
    return Coil.get_defects(coil_id, direction)


@router.get("/search/getDefectAll/{start_coil_id:int}/{end_coil_id:int}")
async def get_defect_all(start_coil_id, end_coil_id):
    return Coil.get_defects_all(start_coil_id, end_coil_id)


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
    data = serverConfigProperty.get_info(coil_id, surface_key)
    if data is None and _test_mode_enabled() and str(coil_id) == get_testdata_coil_id():
        return get_testdata_coil_info(surface_key)
    return data


async def get_camera_config(coil_id: int, surface_key: str, c):
    return serverConfigProperty.getCameraConfig(coil_id, surface_key)


@router.get("/hardware")
async def get_hardware():
    return Hardware.getHardwareInfo()


def _capture_config_file() -> Path:
    capture_dir = Path(CONFIG.base_config_folder) / "capture_config"
    if CONFIG.isLoc and (capture_dir / "CapTureLoc.json").exists():
        return capture_dir / "CapTureLoc.json"
    return capture_dir / "CapTure.json"


def _load_capture_config() -> dict:
    config_file = _capture_config_file()
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取相机配置失败: {e}")
    return data


def _normalize_camera_items(cameras) -> list[dict]:
    if cameras is None:
        return []
    if isinstance(cameras, dict):
        cameras = list(cameras.values())
    if not isinstance(cameras, list):
        return []

    normalized = []
    for index, camera in enumerate(cameras, start=1):
        if not isinstance(camera, dict):
            if hasattr(camera, "__dict__"):
                camera = vars(camera)
            else:
                logger.warning("skip invalid camera config item: %r", camera)
                continue
        item = dict(camera)
        if not item.get("key"):
            item["key"] = item.get("name") or item.get("sn") or f"camera_{index}"
        if not item.get("name"):
            item["name"] = item.get("key")
        normalized.append(item)
    return normalized


def _load_legacy_camera_list() -> list[dict]:
    cameras = getattr(CONFIG, "CameraList", None)
    if cameras is None:
        cameras = getattr(CONFIG, "cameraList", None)
    legacy_cameras = _normalize_camera_items(cameras)
    if legacy_cameras:
        logger.warning("using legacy CONFIG.CameraList camera configuration")
    return legacy_cameras


def _load_capture_cameras() -> list[dict]:
    try:
        data = _load_capture_config()
    except HTTPException as e:
        logger.warning("capture camera config unavailable: %s", e.detail)
        return _load_legacy_camera_list()

    cameras = data.get("camera", [])
    normalized = _normalize_camera_items(cameras)
    if cameras and not normalized:
        logger.warning("capture camera config camera field invalid; fallback to legacy CameraList")
        return _load_legacy_camera_list()
    return normalized


def _normalize_service_host(host: str) -> str:
    if host in {"0.0.0.0", "::", ""}:
        return "127.0.0.1"
    return host


def _capture_service_base_url() -> Optional[str]:
    try:
        config = _load_capture_config()
    except HTTPException:
        return None
    host = _normalize_service_host(str(config.get("apiServerIp") or "127.0.0.1"))
    port = int(config.get("apiServerPort") or 6100)
    return f"http://{host}:{port}"


def _legacy_camera_service_base_url(camera: dict) -> Optional[str]:
    server_port = camera.get("serverPort")
    if server_port is None:
        return None
    host = _normalize_service_host(str(camera.get("serverIp") or "127.0.0.1"))
    return f"http://{host}:{int(server_port)}"


def _camera_service_base_url(camera: dict) -> Optional[str]:
    return _legacy_camera_service_base_url(camera)


def _camera_public_info(camera: dict) -> dict:
    service_url = _capture_service_base_url() or _camera_service_base_url(camera) or ""
    legacy_service_url = _legacy_camera_service_base_url(camera)
    return {
        "key": camera.get("key", ""),
        "name": camera.get("name", ""),
        "sn": camera.get("sn", ""),
        "serverIp": camera.get("serverIp", ""),
        "serverPort": camera.get("serverPort", 0),
        "yamlConfig": camera.get("yaml_config", ""),
        "cap2D": bool(camera.get("cap2D", True)),
        "cap3D": bool(camera.get("cap3D", True)),
        "serviceUrl": service_url or "",
        "legacyServiceUrl": legacy_service_url or "",
    }


def _capture_service_get(path: str, timeout: float | None = None) -> dict:
    base_url = _capture_service_base_url()
    if not base_url:
        return {"ok": False, "message": "capture service config not found", "serviceUrl": ""}
    url = base_url + path
    try:
        request_timeout = (timeout if timeout is not None else
                           _CAMERA_SERVICE_TIMEOUT * 6)
        response = requests.get(url, timeout=request_timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"ok": False, "message": str(e), "serviceUrl": url}
    except ValueError as e:
        return {"ok": False, "message": f"响应解析失败: {e}", "serviceUrl": url}


def _find_capture_camera(camera_key: str) -> dict:
    for camera in _load_capture_cameras():
        if camera.get("key") == camera_key:
            return camera
    raise HTTPException(status_code=404, detail=f"未找到相机: {camera_key}")


def _camera_service_get(camera: dict, path: str) -> dict:
    camera_key = camera.get("key", "")
    capture_base_url = _capture_service_base_url()
    legacy_base_url = _legacy_camera_service_base_url(camera)
    if path == "/camera/status" and not camera_key and not legacy_base_url:
        return {"ok": False, "connected": False, "message": "相机服务端口未配置"}
    if not capture_base_url:
        if not legacy_base_url:
            return {"ok": False, "connected": False, "message": "相机服务端口未配置", "serviceUrl": ""}
        url = legacy_base_url + path
    elif path == "/camera/status":
        url = capture_base_url + f"/cameras/{camera_key}/status"
    else:
        url = capture_base_url + path
    try:
        response = requests.get(url, timeout=_CAMERA_SERVICE_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        if legacy_base_url and path == "/camera/status":
            try:
                response = requests.get(legacy_base_url + path, timeout=_CAMERA_SERVICE_TIMEOUT)
                response.raise_for_status()
                data = response.json()
                data["legacyService"] = True
                return data
            except (requests.RequestException, ValueError) as legacy_exc:
                logger.debug("legacy camera status request failed: %s",
                             legacy_exc)
        return {"ok": False, "connected": False, "message": str(e), "serviceUrl": url}
    except ValueError as e:
        return {"ok": False, "connected": False, "message": f"响应解析失败: {e}"}


def _camera_service_post(camera: dict, path: str, payload: dict | None = None) -> dict:
    camera_key = camera.get("key", "")
    capture_base_url = _capture_service_base_url()
    legacy_base_url = _legacy_camera_service_base_url(camera)
    if not capture_base_url:
        if path in {"/camera/reconnect/3d", "/camera/reset/3d"}:
            raise HTTPException(
                status_code=502,
                detail="capture service is required for 3D camera control",
            )
        if not legacy_base_url:
            raise HTTPException(status_code=502, detail="相机服务端口未配置")
        url = legacy_base_url + path
    elif path == "/camera/params":
        url = capture_base_url + f"/cameras/{camera_key}/params"
    elif path == "/camera/reconnect":
        url = capture_base_url + f"/cameras/{camera_key}/reconnect"
    elif path == "/camera/reconnect/2d":
        url = capture_base_url + f"/cameras/{camera_key}/reconnect/2d"
    elif path == "/camera/reconnect/3d":
        url = capture_base_url + f"/cameras/{camera_key}/reconnect/3d"
    elif path == "/camera/reset/3d":
        url = capture_base_url + f"/cameras/{camera_key}/reset/3d"
    else:
        url = capture_base_url + path
    try:
        response = requests.post(url, json=payload or {}, timeout=_CAMERA_SERVICE_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"响应解析失败: {e}")


def _build_capture_query_path(path: str, clear: bool = False) -> str:
    if clear:
        return f"{path}?clear=true"
    return path


def _camera_capture_item(camera: dict) -> dict:
    camera_key = camera.get("key", "")
    status = _camera_service_get(camera, "/camera/status")
    return {
        **_camera_public_info(camera),
        "status": status,
        "key": status.get("key", camera_key),
    }


def _capture_status_value(realtime: bool = False) -> dict:
    timeout = _CAPTURE_MONITOR_TIMEOUT if realtime else None
    result = _capture_service_get("/capture/status", timeout=timeout)
    if result.get("ok") is not False or result.get("cameras"):
        return result
    if realtime:
        cameras = []
        for camera in _load_capture_cameras():
            cameras.append({
                **_camera_public_info(camera),
                "captureRunning": False,
                "serviceReady": False,
                "camera2D": None,
                "camera3D": None,
                "lastError2D": result.get("message", ""),
                "lastError3D": result.get("message", ""),
            })
        return {
            **result,
            "service": "CapAll",
            "configFile": str(_capture_config_file()),
            "serviceUrl": _capture_service_base_url() or "",
            "cameraCount": len(cameras),
            "cameras": cameras,
        }
    return {
        **result,
        "service": "CapAll",
        "configFile": str(_capture_config_file()),
        "serviceUrl": _capture_service_base_url() or "",
        "cameraCount": len(_load_capture_cameras()),
        "cameras": [_camera_capture_item(camera) for camera in _load_capture_cameras()],
    }


def _camera_monitor_ok(status: dict) -> bool:
    if not status.get("serviceReady", False):
        return False
    if status.get("cap2D"):
        camera_2d = status.get("camera2D") or {}
        if not camera_2d.get("ok", False):
            return False
    if status.get("cap3D"):
        camera_3d = status.get("camera3D") or {}
        if not camera_3d.get("ok", False):
            return False
    return not bool(status.get("lastError2D") or status.get("lastError3D"))


def _hardware_monitor_value() -> dict:
    captured_at = time.time()
    capture_status = _capture_status_value(realtime=True)
    cameras = [
        item for item in capture_status.get("cameras", [])
        if isinstance(item, dict)
    ]
    network_error = ""
    try:
        network_adapters = get_network_adapters()
    except Exception as e:
        logger.exception("read network adapter status failed: %s", e)
        network_adapters = []
        network_error = str(e)

    service_error = ""
    try:
        services = get_service_statuses()
    except Exception as e:
        logger.exception("read service status failed: %s", e)
        services = []
        service_error = str(e)

    camera_online = sum(1 for camera in cameras
                        if _camera_monitor_ok(camera))
    cameras_2d = [camera for camera in cameras if camera.get("cap2D")]
    cameras_3d = [camera for camera in cameras if camera.get("cap3D")]
    camera_2d_online = sum(
        1 for camera in cameras_2d
        if (camera.get("camera2D") or {}).get("ok", False))
    camera_3d_online = sum(
        1 for camera in cameras_3d
        if (camera.get("camera3D") or {}).get("ok", False))
    network_online = sum(1 for adapter in network_adapters
                         if adapter.get("isUp", False))
    service_online = sum(1 for service in services
                         if service.get("online", False))
    temperatures = []
    for camera in cameras:
        for dimension in ("camera2D", "camera3D"):
            status = camera.get(dimension) or {}
            value = status.get("temperatureCelsius")
            if status.get("temperatureAvailable") and isinstance(
                    value, (int, float)):
                temperatures.append(float(value))
    return {
        "ok": (bool(capture_status.get("ok", False))
               and not network_error and not service_error),
        "time": captured_at,
        "captureServiceUrl": _capture_service_base_url() or "",
        "capture": capture_status,
        "cameras": cameras,
        "networkAdapters": network_adapters,
        "networkError": network_error,
        "services": services,
        "serviceError": service_error,
        "summary": {
            "cameraCount": len(cameras),
            "cameraOnline": camera_online,
            "camera2DCount": len(cameras_2d),
            "camera2DOnline": camera_2d_online,
            "camera3DCount": len(cameras_3d),
            "camera3DOnline": camera_3d_online,
            "networkAdapterCount": len(network_adapters),
            "networkAdapterOnline": network_online,
            "serviceCount": len(services),
            "serviceOnline": service_online,
            "temperatureSensorCount": len(temperatures),
            "maxTemperatureCelsius": (
                max(temperatures) if temperatures else None),
        },
    }


def _plc_service_base_url() -> str:
    host = os.getenv("PLC_SERVER_IP", "127.0.0.1")
    host = _normalize_service_host(host)
    try:
        port = int(os.getenv("PLC_SERVER_PORT", "1211"))
    except ValueError:
        port = 1211
    return f"http://{host}:{port}"


def _plc_service_request(method: str, path: str, payload: dict | None = None):
    url = _plc_service_base_url() + path
    try:
        if method == "get":
            response = requests.get(url, timeout=3)
        else:
            response = requests.post(url, json=payload or {}, timeout=3)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"响应解析失败: {e}")


def _payload_to_dict(payload: BaseModel) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


@router.get("/camera_adjust")
def get_camera_adjustments():
    capture_status = _capture_service_get("/capture/status")
    status_by_key = {
        item.get("key"): item
        for item in capture_status.get("cameras", [])
        if isinstance(item, dict)
    }
    camera_items = []
    for camera in _load_capture_cameras():
        info = _camera_public_info(camera)
        status = status_by_key.get(camera.get("key")) or _camera_service_get(camera, "/camera/status")
        status_2d = _camera_2d_status(status)
        if isinstance(status_2d, dict):
            status_2d = {
                **status_2d,
                "capture": status,
                "lastFrameAge3D": status.get("lastFrameAge3D"),
                "lastError3D": status.get("lastError3D", ""),
            }
        camera_items.append({
            **info,
            "status": status_2d,
        })
    return {
        "configFile": str(_capture_config_file()),
        "captureServiceUrl": _capture_service_base_url(),
        "captureStatus": {
            "ok": capture_status.get("ok", False),
            "message": capture_status.get("message", ""),
            "cameraCount": capture_status.get("cameraCount", len(camera_items)),
        },
        "cameras": camera_items,
    }


@router.post("/camera_adjust/{camera_key}")
def set_camera_adjustment(camera_key: str, payload: CameraAdjustmentPayload):
    camera = _find_capture_camera(camera_key)
    return _camera_service_post(camera, "/camera/params", _payload_to_dict(payload))


@router.post("/camera_adjust/{camera_key}/reconnect")
def reconnect_camera_adjustment(camera_key: str):
    camera = _find_capture_camera(camera_key)
    return _camera_service_post(camera, "/camera/reconnect")


@router.get("/capture_status")
def get_capture_status():
    return _capture_status_value()


@router.get("/capture/status")
def get_capture_status_compat():
    return _capture_status_value()


@router.get("/capture/files")
def get_capture_files(clear: bool = False):
    return _capture_service_get(_build_capture_query_path("/capture/files", clear))


@router.get("/getListenerAddFile")
def get_capture_listener_files(clear: bool = False):
    return _capture_service_get(_build_capture_query_path("/getListenerAddFile", clear))


@router.get("/cameras")
def get_cameras():
    result = _capture_service_get("/cameras")
    if result.get("ok") is not False or result.get("cameras"):
        return result
    return {
        **result,
        "service": "CapAll",
        "cameraCount": len(_load_capture_cameras()),
        "cameras": [_camera_capture_item(camera) for camera in _load_capture_cameras()],
    }


@router.get("/cameras/{camera_key}/status")
def get_camera_status_by_key(camera_key: str):
    camera = _find_capture_camera(camera_key)
    return _camera_service_get(camera, "/camera/status")


@router.get("/cameras/{camera_key}/files")
def get_camera_files_by_key(camera_key: str, clear: bool = False):
    camera = _find_capture_camera(camera_key)
    path = _build_capture_query_path(f"/cameras/{camera_key}/files", clear)
    return _camera_service_get(camera, path)


@router.post("/cameras/{camera_key}/params")
def set_camera_params_by_key(camera_key: str, payload: CameraAdjustmentPayload):
    camera = _find_capture_camera(camera_key)
    return _camera_service_post(camera, "/camera/params",
                                _payload_to_dict(payload))


@router.post("/cameras/{camera_key}/reconnect")
def reconnect_camera_by_key(camera_key: str):
    camera = _find_capture_camera(camera_key)
    return _camera_service_post(camera, "/camera/reconnect")


@router.post("/cameras/{camera_key}/reconnect/2d")
def reconnect_camera_2d_by_key(camera_key: str):
    camera = _find_capture_camera(camera_key)
    return _camera_service_post(camera, "/camera/reconnect/2d")


@router.post("/cameras/{camera_key}/reconnect/3d")
def reconnect_camera_3d_by_key(camera_key: str):
    camera = _find_capture_camera(camera_key)
    return _camera_service_post(camera, "/camera/reconnect/3d")


@router.post("/cameras/{camera_key}/reset/3d")
def reset_camera_3d_by_key(camera_key: str):
    camera = _find_capture_camera(camera_key)
    return _camera_service_post(camera, "/camera/reset/3d")


@router.get("/hardware_monitor")
@router.get("/hardware/status")
async def get_hardware_monitor():
    # The main API also serves long-running synchronous image endpoints.
    # Use the event loop's executor so monitor refreshes are not queued behind
    # Starlette's shared synchronous-route worker pool.
    return await asyncio.to_thread(_hardware_monitor_value)


@router.get("/network/adapters")
def get_network_adapter_status():
    return {
        "ok": True,
        "time": time.time(),
        "networkAdapters": get_network_adapters(),
    }


@router.get("/services/status")
async def get_service_status():
    services = await asyncio.to_thread(get_service_statuses)
    return {
        "ok": True,
        "time": time.time(),
        "services": services,
        "summary": {
            "serviceCount": len(services),
            "serviceOnline": sum(
                1 for service in services if service.get("online", False)),
        },
    }


@router.post("/services/{service_key}/restart")
def restart_service_by_key(service_key: str):
    try:
        return restart_service(service_key)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/network/adapters/{adapter_name}/control")
def control_network_adapter_by_name(
        adapter_name: str, payload: NetworkAdapterControlPayload):
    try:
        return control_network_adapter(adapter_name, payload.action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/camera/status")
def get_camera_status():
    cameras = _load_capture_cameras()
    if not cameras:
        raise HTTPException(status_code=404, detail="未找到相机: 无")
    return _camera_service_get(cameras[0], "/camera/status")


@router.post("/camera/params")
def set_camera_params(payload: CameraAdjustmentPayload):
    cameras = _load_capture_cameras()
    if not cameras:
        raise HTTPException(status_code=404, detail="未找到相机: 无")
    return _camera_service_post(cameras[0], "/camera/params",
                                _payload_to_dict(payload))


@router.post("/camera/reconnect")
def reconnect_camera():
    cameras = _load_capture_cameras()
    if not cameras:
        raise HTTPException(status_code=404, detail="未找到相机: 无")
    return _camera_service_post(cameras[0], "/camera/reconnect")


@router.get("/plc/info")
@router.get("/plc/info/")
async def get_plc_info():
    return _plc_service_request("get", "/plc/info/")


@router.get("/plc/connect/{plc_ip}/{rack}/{slot}")
async def connect_plc(plc_ip: str, rack: int, slot: int):
    return _plc_service_request(
        "get",
        f"/plc/connect/{plc_ip}/{rack}/{slot}",
    )


@router.get("/plc/get/{addr}/{type_str}/{length}")
async def read_plc_value(addr: str, type_str: str, length: int):
    if length < 0:
        raise HTTPException(status_code=400, detail="length must be non-negative")
    return _plc_service_request(
        "get",
        f"/plc/get/{addr}/{type_str}/{length}",
    )


def _camera_2d_status(status: dict) -> dict:
    return status.get("camera2D") or status


def _capture_alarm_item(camera: dict, status: dict) -> dict:
    status_2d = _camera_2d_status(status)
    connected = bool(status_2d.get("connected", False))
    ok = bool(status_2d.get("ok", False))
    message = status_2d.get("message") or status.get("lastError3D") or status.get("message") or ""
    last_frame_age = status_2d.get("lastFrameAge", status.get("lastFrameAge2D"))
    level = 1
    if not status.get("serviceReady", True):
        level = 2
        message = message or "采集服务正在初始化"
    if status.get("cap2D", True) and not ok:
        level = 3
        message = message or "2D相机采集异常"
    if status.get("cap3D", True) and status.get("lastError3D"):
        level = 3
        message = status.get("lastError3D")
    return {
        "DeviceTemperature": status_2d.get("DeviceTemperature", 0),
        "level": level,
        "msg": message or "采集正常",
        "connected": connected,
        "ok": ok and level == 1,
        "captureOk": level == 1,
        "lastFrameAge": last_frame_age,
        "lastError2D": status.get("lastError2D", ""),
        "lastError3D": status.get("lastError3D", ""),
        "serviceUrl": _capture_service_base_url(),
        "cameraKey": camera.get("key", ""),
        "cameraName": camera.get("name", ""),
    }


def _camera_alarm_error_item(name: str, message: str, level: int = 2) -> dict:
    return {
        "DeviceTemperature": 0,
        "level": level,
        "msg": message,
        "connected": False,
        "ok": False,
        "captureOk": False,
        "lastFrameAge": None,
        "lastError2D": message,
        "lastError3D": "",
        "serviceUrl": _capture_service_base_url() or "",
        "cameraKey": name,
        "cameraName": name,
    }


def _demo_camera_alarm_payload() -> Optional[dict]:
    if not CONFIG.isLoc:
        return None
    demo_file = _PROJECT_ROOT / "demo" / "camera_config.json"
    if not demo_file.exists():
        logger.debug("local camera demo config not found: %s", demo_file)
        return None
    try:
        camera_config = json.loads(demo_file.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("local camera demo config read failed: %s", e)
        return None
    return {
        "S_D": {**camera_config, "level": 1, "msg": "近端下方相机（右键打开设置）"},
        "S_M": {**camera_config, "level": 1, "msg": "近端中间相机（右键打开设置）"},
        "S_U": {**camera_config, "level": 1, "msg": "近端上方相机（右键打开设置）"},
        "L_D": {**camera_config, "level": 1, "msg": "远端下方相机（右键打开设置）"},
        "L_M": {**camera_config, "level": 1, "msg": "远端中间相机（右键打开设置）"},
        "L_U": {**camera_config, "level": 1, "msg": "远端上方相机（右键打开设置）"},
    }


@router.get("/cameraAlarm")
async def get_camera_alarm():
    """
      获取相机报警信息
    Returns:
    """
    demo_payload = _demo_camera_alarm_payload()
    if demo_payload is not None:
        return demo_payload

    capture_status = _capture_service_get("/capture/status")
    status_by_key = {
        item.get("key"): item
        for item in capture_status.get("cameras", [])
        if isinstance(item, dict)
    }
    result = {}
    cameras = _load_capture_cameras()
    if not cameras:
        return {
            "相机配置": _camera_alarm_error_item(
                "相机配置",
                "未找到相机配置，请检查 capture_config/CapTure.json 或 CONFIG.CameraList",
            )
        }
    for camera in cameras:
        status = status_by_key.get(camera.get("key")) or _camera_service_get(camera, "/camera/status")
        result[camera.get("name") or camera.get("key", "")] = _capture_alarm_item(camera, status)
    return result


@router.get("/cameraData/{coil_id:int}/{camera_key:str}")
async def get_camera_data(coil_id: int, camera_key: str):
    if CONFIG.isLoc:
        with open("demo/camera_config.json", "r", encoding="utf-8") as f:
            camera_config = json.load(f)
            return camera_config

    return serverConfigProperty.getCameraData(coil_id, camera_key)


@router.get("/backupImageTask/{from_id:int}/{to_id:int}/{save_folder:path}")
async def backup_image_task(from_id: int, to_id: int, save_folder: str):
    logger.info(
        "backup image task requested: from_id=%s to_id=%s save_folder=%s",
        from_id,
        to_id,
        save_folder,
    )
    return Backup.backup_image_task(from_id, to_id, save_folder)


@router.get("/get_point_data/{coil_id:int}/{surface_key:str}")
async def get_point_data(coil_id: int, surface_key: str):
    """
    获取点数据
    """
    surface_key = get_surface_key(surface_key)
    return await run_in_threadpool(
        lambda: tool.to_dict(Coil.get_point_data(coil_id, surface_key)))


@router.get("/get_line_data/{coil_id:int}/{surface_key:str}")
async def get_line_data(coil_id: int, surface_key: str):
    surface_key = get_surface_key(surface_key)
    return await run_in_threadpool(
        lambda: tool.to_dict(Coil.get_line_data(coil_id, surface_key)))


@router.get("/check/get_coil_status/{coil_id:int}")
async def get_coil_status(coil_id):
    item = tool.to_dict(get_coil_status_by_coil_id(coil_id))
    if not item:
        item = {"status": 0, "msg": "", "secondaryCoilId": coil_id, "Id": -1}
    return item


@router.get("/check/set_coil_status/{coil_id:int}/{status:int}/{msg:str}")
@router.get("/check/set_coil_status/{coil_id:int}/{status:int}")
async def set_coil_status(coil_id, status, msg=""):
    set_coil_status_by_data(coil_id, status, msg)


@router.get("/detail/{coil_id:int}")
async def get_coil_detail_api(coil_id: int):
    """
    获取卷材详情（完整数据）
    包括：基本信息、报警详情、缺陷列表、塔形点数据、松卷/扁卷报警等
    用于点击查看详情时调用
    """
    detail = get_coil_detail(coil_id)
    if detail is None:
        return {"error": "Coil not found"}
    return detail


@router.get("/coilAlarm/get_info")
async def get_coil_alarm_info():
    return None


@router.get("/coilAlarm/{coil_id:int}")
async def get_coil_alarm(coil_id: int):
    return _load_coil_alarm_payload(coil_id)


@router.post("/sync_summaries")
async def sync_summaries_api(limit: int = 1000):
    """
    手动触发批量同步摘要数据
    用于初始化摘要表
    """
    count = batch_sync_summaries(limit=limit)
    return {"synced": count, "message": f"Synced {count} summaries"}


@router.post("/sync_summaries_range")
async def sync_summaries_range_api(request: dict):
    """
    快速同步指定 ID 范围的摘要数据
    只更新已存在的记录，不创建新记录
    主要用于更新 DefectCountS/L 和 MaxDefect 字段
    """
    from CoilDataBase.CoilSummary import sync_summaries_range
    coil_ids = request.get("coil_ids", [])
    if not coil_ids:
        return {"error": "coil_ids is required", "synced": 0}
    count = sync_summaries_range(coil_ids)
    return {"synced": count, "message": f"Updated {count} summaries"}


def _safe_folder_name(value: str) -> str:
    name = str(value or "Unknown").strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", name)
    return name.strip(" .") or "Unknown"


def _load_defect_data(value) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if not value:
        return {}
    try:
        data = json.loads(value)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _center_crop_with_padding(image, center_x: float, center_y: float,
                              crop_w: int, crop_h: int):
    img_w, img_h = image.size
    crop_w = min(max(int(crop_w), 1), max(img_w, 1))
    crop_h = min(max(int(crop_h), 1), max(img_h, 1))
    left = int(round(center_x - crop_w / 2))
    top = int(round(center_y - crop_h / 2))
    right = left + crop_w
    bottom = top + crop_h

    source_left = max(0, left)
    source_top = max(0, top)
    source_right = min(img_w, right)
    source_bottom = min(img_h, bottom)
    crop = image.crop((source_left, source_top, source_right, source_bottom))

    if crop.size == (crop_w, crop_h):
        return crop, (left, top, right, bottom)

    background = 0
    if image.mode == "RGBA":
        background = (0, 0, 0, 0)
    elif image.mode == "RGB":
        background = (0, 0, 0)
    padded = Image.new(image.mode, (crop_w, crop_h), background)
    padded.paste(crop, (source_left - left, source_top - top))
    return padded, (left, top, right, bottom)


def _write_manual_defect_xml(xml_path: Path, image_path: Path, image_size,
                             bbox, defect_name: str) -> None:
    import xml.etree.ElementTree as ET

    width, height = image_size
    xmin, ymin, xmax, ymax = bbox
    annotation = ET.Element("annotation")
    ET.SubElement(annotation, "folder").text = image_path.parent.name
    ET.SubElement(annotation, "filename").text = image_path.name

    size = ET.SubElement(annotation, "size")
    ET.SubElement(size, "width").text = str(width)
    ET.SubElement(size, "height").text = str(height)
    ET.SubElement(size, "depth").text = "3"

    obj = ET.SubElement(annotation, "object")
    ET.SubElement(obj, "name").text = defect_name
    bndbox = ET.SubElement(obj, "bndbox")
    ET.SubElement(bndbox, "xmin").text = str(xmin)
    ET.SubElement(bndbox, "ymin").text = str(ymin)
    ET.SubElement(bndbox, "xmax").text = str(xmax)
    ET.SubElement(bndbox, "ymax").text = str(ymax)

    tree = ET.ElementTree(annotation)
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)


def _save_manual_defect_assets(defect: dict) -> dict:
    from Base.tools.DataGet import DataGet

    defect_id = int(defect.get("Id") or 0)
    coil_id = int(defect.get("secondaryCoilId") or 0)
    surface = defect.get("surface") or "S"
    defect_name = defect.get("defectName") or "Unknown"
    x = int(defect.get("defectX") or 0)
    y = int(defect.get("defectY") or 0)
    w = max(int(defect.get("defectW") or 1), 1)
    h = max(int(defect.get("defectH") or 1), 1)

    try:
        image = DataGet("image", surface, str(coil_id), "GRAY",
                        False).get_image(pil=True)
        if image is None:
            return {"manualAssetError": "source image not found"}

        center_x = x + w / 2
        center_y = y + h / 2
        crop_w = max(int(round(w * 1.4)), 128)
        crop_h = max(int(round(h * 1.4)), 128)
        crop_image, crop_box = _center_crop_with_padding(
            image, center_x, center_y, crop_w, crop_h)
        if crop_image.mode not in {"RGB", "L"}:
            crop_image = crop_image.convert("RGB")

        base_dir = Path(serverConfigProperty.get_folder(coil_id, surface))
        category_dir = base_dir / "manual_defect" / _safe_folder_name(
            defect_name)
        category_dir.mkdir(parents=True, exist_ok=True)

        file_stem = f"{coil_id}_{surface}_{defect_id}_x{x}_y{y}_w{w}_h{h}"
        image_path = category_dir / f"{file_stem}.jpg"
        xml_path = category_dir / f"{file_stem}.xml"
        crop_image.save(image_path, quality=95)

        left, top, _, _ = crop_box
        local_xmin = max(0, min(crop_image.size[0] - 1, int(round(x - left))))
        local_ymin = max(0, min(crop_image.size[1] - 1, int(round(y - top))))
        local_xmax = max(local_xmin + 1,
                         min(crop_image.size[0], int(round(x + w - left))))
        local_ymax = max(local_ymin + 1,
                         min(crop_image.size[1], int(round(y + h - top))))
        _write_manual_defect_xml(
            xml_path,
            image_path,
            crop_image.size,
            (local_xmin, local_ymin, local_xmax, local_ymax),
            defect_name,
        )

        return {
            "manualImagePath": str(image_path),
            "manualXmlPath": str(xml_path),
            "manualCropBox": list(crop_box),
            "manualCenter": [center_x, center_y],
        }
    except Exception as e:
        return {"manualAssetError": str(e)}


def _sync_manual_defect_assets(manual_defect):
    defect = tool.to_dict(manual_defect)
    asset_data = _save_manual_defect_assets(defect)
    defect_data = _load_defect_data(defect.get("defectData"))
    defect_data.update(asset_data)
    updated = Coil.update_manual_defect(
        defect["Id"],
        {"defectData": json.dumps(defect_data, ensure_ascii=False)},
    )
    return updated or manual_defect


def _get_manual_image_path(defect_data: dict) -> Path | None:
    extra_data = _load_defect_data(defect_data.get("defectData"))
    image_path = extra_data.get("manualImagePath")
    if not image_path:
        return None
    path = Path(image_path)
    return path if path.exists() else None


@router.get("/search/defects_all/{coil_id:int}/{direction}")
async def get_defects_all_including_manual(coil_id: int, direction: str):
    """
    获取所有缺陷（包括自动检测和手动标注）

    Args:
        coil_id: 二级卷ID
        direction: 表面标识（S/L）

    Returns:
        包含自动检测缺陷和手动标注缺陷的列表
    """
    return Coil.get_all_defects_including_manual(coil_id, direction)


@router.get("/manual_defects/{coil_id:int}/{direction}")
async def get_manual_defects_api(coil_id: int, direction: str):
    """
    获取手动标注的缺陷列表

    Args:
        coil_id: 二级卷ID
        direction: 表面标识（S/L）

    Returns:
        手动标注缺陷列表
    """
    return Coil.get_manual_defect_dicts(coil_id, direction)


@router.post("/manual_defect/add")
async def add_manual_defect_api(request: dict):
    """
    添加手动标注的缺陷

    Args:
        request: 缺陷数据字典，包含：
            - secondaryCoilId: 二级卷ID
            - surface: 表面标识（S/L）
            - defectName: 缺陷名称
            - defectX: X坐标
            - defectY: Y坐标
            - defectW: 宽度
            - defectH: 高度
            - remark: 备注（可选）
            - annotator: 标注人（可选）

    Returns:
        创建的缺陷数据
    """
    try:
        manual_defect = Coil.add_manual_defect(request)
        manual_defect = _sync_manual_defect_assets(manual_defect)
        return tool.to_dict(manual_defect)
    except Exception as e:
        return {"error": str(e), "success": False}


@router.put("/manual_defect/update/{defect_id:int}")
async def update_manual_defect_api(defect_id: int, request: dict):
    """
    更新手动标注的缺陷

    Args:
        defect_id: 缺陷ID
        request: 更新的数据字典

    Returns:
        更新后的缺陷数据，如果不存在返回错误
    """
    try:
        manual_defect = Coil.update_manual_defect(defect_id, request)
        if manual_defect is None:
            return {"error": "缺陷不存在", "success": False}
        manual_defect = _sync_manual_defect_assets(manual_defect)
        return tool.to_dict(manual_defect)
    except Exception as e:
        return {"error": str(e), "success": False}


@router.delete("/manual_defect/delete/{defect_id:int}")
async def delete_manual_defect_api(defect_id: int):
    """
    删除手动标注的缺陷

    Args:
        defect_id: 缺陷ID

    Returns:
        删除结果
    """
    try:
        success = Coil.delete_manual_defect(defect_id)
        if success:
            return {"success": True, "message": "删除成功"}
        else:
            return {"error": "缺陷不存在", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


@router.post("/export_defects")
async def export_defects(request: dict):
    """
    导出当前显示的缺陷图像到本地文件夹

    Args:
        request: 包含 defects（缺陷列表）和 folder_path（导出路径）的字典

    Returns:
        导出结果统计
    """
    from pathlib import Path
    from Base.utils.export.export_image import (
        _close_source_image_cache,
        get_pil_image_for_export,
    )
    from CoilDataBase.models.CoilDefect import CoilDefect

    # 安全检查：只允许本地路径
    if not isLoc:
        return {"error": "仅支持本地服务器导出", "exported": 0}

    # 获取参数
    defects = request.get("defects", [])
    folder_path = request.get("folder_path", "")

    if not folder_path:
        return {"error": "请指定导出文件夹路径", "exported": 0}

    if not defects:
        return {"error": "没有可导出的缺陷数据", "exported": 0}

    # 创建导出目录
    export_base = Path(folder_path)
    try:
        export_base.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return {"error": f"无法创建目录: {e}", "exported": 0}

    # 按缺陷类别分组
    defect_groups = {}
    for defect in defects:
        defect_name = defect.get("defectName", "Unknown")
        if defect_name not in defect_groups:
            defect_groups[defect_name] = []
        defect_groups[defect_name].append(defect)

    exported_count = 0
    error_count = 0
    source_image_cache = {}

    # 导出每个缺陷
    for defect_name, defect_list in defect_groups.items():
        # 为每个类别创建子文件夹
        category_folder = export_base / defect_name
        category_folder.mkdir(exist_ok=True)

        for idx, defect_data in enumerate(defect_list):
            try:
                # 获取缺陷参数
                coil_id = defect_data.get("secondaryCoilId", 0)
                surface = defect_data.get("surface", "S")
                defect_x = defect_data.get("defectX", 0)
                defect_y = defect_data.get("defectY", 0)
                defect_w = defect_data.get("defectW", 100)
                defect_h = defect_data.get("defectH", 100)

                # 创建 CoilDefect 对象
                coil_defect = CoilDefect()
                coil_defect.secondaryCoilId = coil_id
                coil_defect.surface = surface
                coil_defect.defectName = defect_name
                coil_defect.defectX = defect_x
                coil_defect.defectY = defect_y
                coil_defect.defectW = defect_w
                coil_defect.defectH = defect_h
                coil_defect.defectData = defect_data.get("defectData", "")

                # 获取缺陷图像
                manual_image_path = _get_manual_image_path(defect_data)
                if manual_image_path is not None:
                    with Image.open(manual_image_path) as image:
                        defect_image = image.copy()
                else:
                    defect_image = get_pil_image_for_export(
                        coil_defect, source_image_cache, defect_name)
                if defect_image is None:
                    raise FileNotFoundError("defect image not found")

                # 生成文件名：coil_id_类别_位置_序号.jpg
                x_pos = int(defect_x)
                y_pos = int(defect_y)
                filename = f"{coil_id}_{defect_name}_x{x_pos}_y{y_pos}_{idx+1}.jpg"

                # 保存图像
                save_path = category_folder / filename
                defect_image.save(save_path, quality=95)
                try:
                    defect_image.close()
                except Exception as close_exc:
                    logger.debug("manual defect image close failed: %s",
                                 close_exc)
                exported_count += 1

            except Exception as e:
                error_count += 1
                logger.warning(
                    "export defect image failed: coil_id=%s defect=%s error=%s",
                    coil_id,
                    defect_name,
                    e,
                )

    _close_source_image_cache(source_image_cache)

    return {
        "exported": exported_count,
        "errors": error_count,
        "categories": len(defect_groups),
        "total": len(defects),
        "message": f"成功导出 {exported_count} 个缺陷图像到 {folder_path}"
    }


app.include_router(router)
