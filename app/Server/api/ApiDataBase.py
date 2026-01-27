import datetime
import json
from collections import defaultdict

from sqlalchemy import func

from fastapi import APIRouter

from Base import CONFIG
from Base.CONFIG import isLoc, serverConfigProperty
from CoilDataBase import Coil, tool
from CoilDataBase.core import Session
from CoilDataBase.Coil import get_coil_status_by_coil_id, set_coil_status_by_data
from CoilDataBase.CoilSummary import get_coil_list_with_summary, get_coil_list_hybrid, get_coil_detail, batch_sync_summaries
from CoilDataBase.models import AlarmInfo, SecondaryCoil, CoilDefect, PlcData, CoilState
from Base.property.ServerConfigProperty import ServerConfigProperty
from Base.utils import Hardware, Backup, export
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
     格式化 单个 Communication 返回 数据
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
     格式化 Communication 返回 数据
    """
    return [format_secondary_item_data(secondary_coil) for secondary_coil in secondary_coil_list]


@router.get("/coilList/{number}")
async def get_coil(number: int, coil_id=None, rev=True):
    """
    获取 n 条数据（仅查询摘要表，不自动同步）

    摘要表由算法检测结束时自动更新，确保数据一致性
    """
    number = min(number, 1000)
    # 直接查询摘要表，不进行自动同步
    data = get_coil_list_with_summary(
        limit=number,
        coil_id=coil_id,
        rev=rev,
        by_coil=isLoc,
        auto_sync=False  # 禁用自动同步
    )
    return data


@router.get("/flush/{coil_id:int}")
async def get_flush(coil_id: int):
    """
    向上刷新（仅查询摘要表）
    """
    if coil_id > 0:
        return {
            "coilList": get_coil_list_with_summary(
                limit=10,
                coil_id=coil_id,
                rev=True,
                by_coil=isLoc,
                auto_sync=False  # 禁用自动同步
            )
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





def _query_plc_curve_rows(start_id: int = 0, end_id: int = 0, limit: int = 200):
    limit = min(max(int(limit), 1), 2000)
    if start_id and end_id and start_id > end_id:
        start_id, end_id = end_id, start_id

    order_desc = not start_id and not end_id

    with Session() as session:
        base_query = session.query(
            PlcData.secondaryCoilId,
            func.max(PlcData.Id).label("max_id")
        )
        if start_id:
            base_query = base_query.filter(PlcData.secondaryCoilId >= start_id)
        if end_id:
            base_query = base_query.filter(PlcData.secondaryCoilId <= end_id)
        base_query = base_query.group_by(PlcData.secondaryCoilId).subquery()

        query = session.query(PlcData).join(base_query, PlcData.Id == base_query.c.max_id)
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
async def get_plc_curve(field: str, start_id: int = 0, end_id: int = 0, limit: int = 200):
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
        base_query = session.query(
            PlcData.secondaryCoilId,
            func.max(PlcData.Id).label("max_id")
        )
        if start_id:
            base_query = base_query.filter(PlcData.secondaryCoilId >= start_id)
        if end_id:
            base_query = base_query.filter(PlcData.secondaryCoilId <= end_id)
        base_query = base_query.group_by(PlcData.secondaryCoilId).subquery()

        query = session.query(PlcData).join(base_query, PlcData.Id == base_query.c.max_id)
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
async def get_plc_curve_all(start_id: int = 0, end_id: int = 0, limit: int = 200):
    rows = _query_plc_curve_rows(start_id, end_id, limit)
    coil_ids = [row.secondaryCoilId for row in rows]
    state_map = {}
    width_map = {}
    if coil_ids:
        with Session() as session:
            state_sub = session.query(
                CoilState.secondaryCoilId.label("coil_id"),
                CoilState.surface.label("surface"),
                func.max(CoilState.Id).label("max_id")
            ).filter(
                CoilState.secondaryCoilId.in_(coil_ids),
                CoilState.surface.in_(["S", "L"])
            ).group_by(CoilState.secondaryCoilId, CoilState.surface).subquery()
            state_rows = session.query(CoilState).join(state_sub, CoilState.Id == state_sub.c.max_id).all()
            width_rows = session.query(SecondaryCoil.Id, SecondaryCoil.ActWidth).filter(SecondaryCoil.Id.in_(coil_ids)).all()
        for state in state_rows:
            state_map[(state.secondaryCoilId, state.surface)] = state.median_3d_mm
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
    return tool.to_dict(Coil.get_defects(coil_id, direction))


@router.get("/search/getDefectAll/{start_coil_id:int}/{end_coil_id:int}")
async def get_defect_all(start_coil_id, end_coil_id):
    return tool.to_dict(Coil.get_defects_all(start_coil_id, end_coil_id))


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


@router.post("/sync_summaries")
async def sync_summaries_api(limit: int = 1000):
    """
    手动触发批量同步摘要数据
    用于初始化摘要表
    """
    count = batch_sync_summaries(limit=limit)
    return {"synced": count, "message": f"Synced {count} summaries"}


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
    from Base.tools.DataGet import get_pil_image_by_defect
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

                # 获取缺陷图像
                defect_image = get_pil_image_by_defect(coil_defect)

                # 生成文件名：coil_id_类别_位置_序号.jpg
                x_pos = int(defect_x)
                y_pos = int(defect_y)
                filename = f"{coil_id}_{defect_name}_x{x_pos}_y{y_pos}_{idx+1}.jpg"

                # 保存图像
                save_path = category_folder / filename
                defect_image.save(save_path, quality=95)
                exported_count += 1

            except Exception as e:
                error_count += 1
                print(f"导出缺陷失败: {e}")

    return {
        "exported": exported_count,
        "errors": error_count,
        "categories": len(defect_groups),
        "total": len(defects),
        "message": f"成功导出 {exported_count} 个缺陷图像到 {folder_path}"
    }


app.include_router(router)
