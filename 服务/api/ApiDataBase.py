import datetime
import json
import os

from fastapi.responses import StreamingResponse
from fastapi import WebSocket

import Globs
from CoilDataBase.models import SecondaryCoil, AlarmInfo
from fastapi.responses import FileResponse
from CoilDataBase import Coil, tool
from AlarmDetection import AlarmCoilManagement
from CONFIG import isLoc
from property.ServerConfigProperty import ServerConfigProperty

from utils import Hardware, Backup, export
from .ApiBase import *
serverConfigProperty: ServerConfigProperty


def get_coil_item_info(c):
    c = tool.to_dict(c)
    if "Weight" in c:
        code = chr(int(c["Weight"]))
        if "Weight" in c:
            c["NextCode"] = code
            try:
                c["NextInfo"] = Globs.infoConfigProperty.getNext(str(code))
            except (Exception,) as e:
                print(e)
                c["NextInfo"] = "未知去向，" + str(code)
    return c


def format_coil_info(secondary_coil_list):
    re = []
    for secondaryCoil in secondary_coil_list:
        secondaryCoil: SecondaryCoil
        c_data = {"hasCoil": False,
                  "hasAlarmInfo": False
                  }

        if len(secondaryCoil.childrenCoil) > 0:
            c_data["hasCoil"] = True
        for childrenCoil in secondaryCoil.childrenCoil:
            c_data.update(get_coil_item_info(childrenCoil))
        c_data["AlarmInfo"] = {}

        if len(secondaryCoil.childrenAlarmInfo) > 0:
            c_data["hasAlarmInfo"] = True
        for childrenAlarmInfo in secondaryCoil.childrenAlarmInfo:
            childrenAlarmInfo: AlarmInfo
            c_data["AlarmInfo"][childrenAlarmInfo.surface] = get_coil_item_info(childrenAlarmInfo)
        c_data.update(get_coil_item_info(secondaryCoil))
        re.append(c_data)
    return re


@app.get("/coilList/{number}")
async def get_coil(number: int):
    return format_coil_info(Coil.getCoilList(number, byCoil=isLoc)[::-1])


@app.get("/flush/{coil_id:int}")
def get_flush(coil_id: int):
    return {
        "coilList": format_coil_info(Coil.getCoilList(10, coil_id, byCoil=isLoc)[::-1])
    }


@app.get("/search/coilNo/{coil_no:str}")
async def search_by_coil_no(coil_no:str):
    return format_coil_info(Coil.searchByCoilNo(coil_no))


@app.get("/search/coilId/{coil_id}")
async def search_by_coil_id(coil_id: int):
    coil_id = int(coil_id)
    return format_coil_info(Coil.searchByCoilId(coil_id))


@app.get("/search/DateTime/{start:str}/{end:str}")
async def search_by_date_time(start: str, end: str):
    start = datetime.datetime.strptime(start, "%Y%m%d%H%M")
    end = datetime.datetime.strptime(end, "%Y%m%d%H%M")
    return format_coil_info(Coil.searchByDateTime(start, end))


@app.get("/search/CoilState/{coil_id:int}")
async def get_coil_state(coil_id: int):
    coil_id = int(coil_id)
    r = Coil.getCoilState(coil_id)
    return tool.to_dict(r)


@app.get("/search/PlcData/{coil_id:int}")
async def get_plc_data(coil_id: int):
    coil_id = int(coil_id)
    r = Coil.getPlcData(coil_id)
    return tool.to_dict(r)


@app.get("/search/defects/{coil_id:int}/{direction}")
async def get_defects(coil_id: int, direction: str):
    return tool.to_dict(Coil.getDefects(coil_id, direction))


@app.get("/search/defectDict")
async def get_defect_dict():
    return tool.to_dict(Coil.getDefetClassDict())


@app.get("/defectDictAll")
async def get_defect_dict_all():
    """
    获取全部的表面缺陷数据字段
    """
    return tool.to_dict(Coil.getDefetClassDict())


@app.get("/coilInfo/{coil_id:int}/{surface_key:str}")
async def get_info(coil_id: int, surface_key: str):
    return serverConfigProperty.get_info(coil_id, surface_key)


async def get_camera_config(coil_id: int, surface_key: str, c):
    return serverConfigProperty.getCameraConfig(coil_id, surface_key)


@app.get("/hardware")
async def get_hardware():
    return Hardware.getHardwareInfo()


@app.get("/cameraAlarm")
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


@app.get("/cameraData/{coil_id:int}/{camera_key:str}")
async def get_camera_data(coil_id: int, camera_key: str):
    if CONFIG.isLoc:
        with open("demo/camera_config.json", "r", encoding="utf-8") as f:
            camera_config = json.load(f)
            return camera_config

    return serverConfigProperty.getCameraData(coil_id, camera_key)


@app.get("/coilAlarm/{coil_id:int}")
async def get_coil_alarm(coil_id: int):
    """
    返回全部的警告数据
    Args:
        coil_id:

    Returns:

    """
    return AlarmCoilManagement.get_coil_alarm(coil_id)


@app.get("/backupImageTask/{from_id:int}/{to_id:int}/{save_folder:path}")
async def backup_image_task(from_id: int, to_id: int, save_folder: str):
    print(from_id)
    print(to_id)
    print(save_folder)
    return Backup.backup_image_task(from_id, to_id, save_folder)


@app.websocket("/ws/backupImageTask")
async def ws_backup_image_task(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            # 接收客户端发送的消息
            data = await websocket.receive_text()
            data = json.loads(data)
            fromId = data['from_id']
            toId = data['to_id']
            saveFolder = data['folder']

            async def msgFunc_(value):
                await websocket.send_text(str(value))

            await Backup.backup_image_task(fromId, toId, saveFolder)
            # 处理并响应数据
            await websocket.send_text(str(100))

        except Exception as e:
            print(f"Connection error: {e}")
            break


@app.get("/exportxlsxByDateTime/{start:str}/{end:str}")
async def export_xlsx_by_datetime(start, end):
    start = datetime.datetime.strptime(start, "%Y%m%d%H%M")
    end = datetime.datetime.strptime(end, "%Y%m%d%H%M")
    output, file_size = export.exportDataByTime(
        start, end
    )

    headers = {
        "Content-Disposition": f"attachment; filename=example.xlsx",
        "Content-Length": str(file_size)  # 设置文件大小
    }

    # 将 BytesIO 对象传递给 StreamingResponse，设置内容类型和附件名称
    response = StreamingResponse(output, headers=headers,
                                 media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    return response


@app.get("/download_test")
async def download_file():
    file_path = "./test/zipdir.zip"
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename="downloaded_file.zip", media_type='application/octet-stream')
    else:
        return {"error": "File not found"}


@app.get("/get_point_data/{coil_id:int}/{surface_key:str}")
async def get_point_data(coil_id: int, surface_key: str):
    """
    获取点数据
    """
    surface_key = get_surface_key(surface_key)
    return tool.to_dict(Coil.get_point_data(coil_id, surface_key))


@app.get("/get_line_data/{coil_id:int}/{surface_key:str}")
async def get_line_data(coil_id: int, surface_key: str):
    surface_key = get_surface_key(surface_key)
    return tool.to_dict(Coil.get_line_data(coil_id, surface_key))
