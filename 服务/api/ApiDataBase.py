import datetime
import json
import os

from fastapi.responses import StreamingResponse
from fastapi import WebSocket
from CoilDataBase.models import SecondaryCoil, AlarmInfo
from fastapi.responses import FileResponse
import Init
from CoilDataBase import Coil
import CONFIG
from AlarmDetection import AlarmCoilManagement
from CONFIG import serverConfigProperty, isLoc
from property.ServerConfigProperty import ServerConfigProperty
from .api_core import app

from utils import Hardware, Backup, export

serverConfigProperty: ServerConfigProperty


@app.get("/")
def read_root():
    return {"docs": "请访问 /docs 查看文档"}


@app.get("/version")
def read_version():
    return CONFIG.VERSION


def getCoilItemInfo(c):
    c = Coil.to_dict(c)
    if "Weight" in c:
        code = chr(int(c["Weight"]))
        if "Weight" in c:
            c["NextCode"] = code
            try:
                c["NextInfo"] = CONFIG.infoConfigProperty.getNext(str(code))
            except:
                c["NextInfo"] = "未知去向，" + str(code)
    return c


def formatCoilInfo(secondaryCoilList):
    re = []
    for secondaryCoil in secondaryCoilList:
        secondaryCoil: SecondaryCoil
        c_data = {"hasCoil": False,
                  "hasAlarmInfo": False
                  }

        if len(secondaryCoil.childrenCoil) > 0:
            c_data["hasCoil"] = True
        for childrenCoil in secondaryCoil.childrenCoil:
            c_data.update(getCoilItemInfo(childrenCoil))
        c_data["AlarmInfo"] = {}

        if len(secondaryCoil.childrenAlarmInfo) > 0:
            c_data["hasAlarmInfo"] = True
        for childrenAlarmInfo in secondaryCoil.childrenAlarmInfo:
            childrenAlarmInfo: AlarmInfo
            c_data["AlarmInfo"][childrenAlarmInfo.surface] = getCoilItemInfo(childrenAlarmInfo)
        c_data.update(getCoilItemInfo(secondaryCoil))
        re.append(c_data)
    return re


@app.get("/coilList/{number}")
def get_coil(number: int):
    re = []
    return formatCoilInfo(Coil.getCoilList(number, byCoil=isLoc)[::-1])


@app.get("/info")
def info():
    info_ = {
        "ErrorMap": Init.ErrorMap,
        "RendererList": CONFIG.RendererList,
        "ColorMaps": Init.ColorMaps,
        "SaveImageType": CONFIG.SaveImageType,
        "PreviewSize": Init.PreviewSize,
    }
    info_.update(serverConfigProperty.to_dict())
    return info_


@app.get("/flush/{coilId:int}")
def flush(coilId: int):
    re = {
        "coilList": formatCoilInfo(Coil.getCoilList(10, coilId, byCoil=isLoc)[::-1])
    }
    return re


@app.get("/search/coilNo/{coilNo}")
def searchByCoilNo(coilNo):
    return formatCoilInfo(Coil.searchByCoilNo(coilNo))


@app.get("/search/coilId/{coilId}")
def searchByCoilId(coilId: int):
    coilId = int(coilId)
    return formatCoilInfo(Coil.searchByCoilId(coilId))


@app.get("/search/DateTime/{start}/{end}")
def searchByDateTime(start: str, end: str):
    re = []
    start = datetime.datetime.strptime(start, "%Y%m%d%H%M")
    end = datetime.datetime.strptime(end, "%Y%m%d%H%M")
    return formatCoilInfo(Coil.searchByDateTime(start, end))


@app.get("/search/CoilState/{coilId:int}")
def getCoilState(coilId: int):
    coilId = int(coilId)
    r = Coil.getCoilState(coilId)
    # print(r)
    return Coil.to_dict(r)


@app.get("/search/PlcData/{coilId:int}")
def getPlcData(coilId: int):
    coilId = int(coilId)
    r = Coil.getPlcData(coilId)
    # print(r)
    return Coil.to_dict(r)


@app.get("/search/defects/{coilId:int}/{direction}")
def getDefects(coilId: int, direction: str):
    return Coil.to_dict(Coil.getDefects(coilId, direction))


@app.get("/search/defectDict")
def getDefectDict():
    return Coil.to_dict(Coil.getDefetClassDict())


@app.get("/coilInfo/{coil_id:str}/{surfaceKey:str}")
async def getInfo(coil_id: str, surfaceKey: str):
    return serverConfigProperty.get_Info(coil_id, surfaceKey)


@app.get("/delay")
async def getDelay():
    return 0


async def getCameraConfig(coil_id: str, surfaceKey: str, c):
    return serverConfigProperty.getCameraConfig(coil_id, surfaceKey)


@app.get("/hardware")
async def getHardware():
    return Hardware.getHardwareInfo()


@app.get("/cameraAlarm")
async def getCameraAlarm():
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


@app.get("/cameraData/{coil_id:str}/{cameraKey:str}")
async def getCameraData(coil_id: str, cameraKey: str):
    if CONFIG.isLoc:
        with open("demo/camera_config.json", "r", encoding="utf-8") as f:
            camera_config = json.load(f)
            return camera_config

    return serverConfigProperty.getCameraData(coil_id, cameraKey)


@app.get("/coilAlarm/{coil_id:str}")
async def getCoilAlarm(coil_id: str):
    """
    返回全部的警告数据
    Args:
        coil_id:

    Returns:

    """
    return AlarmCoilManagement.getCoilAlarm(coil_id)


@app.get("/backupImageTask/{fromId:str}/{toId:str}/{saveFolder:path}")
def backupImageTask(fromId: str, toId: str, saveFolder: str):
    print(fromId)
    print(toId)
    print(saveFolder)
    return Backup.backupImageTask(fromId, toId, saveFolder)


@app.websocket("/ws/backupImageTask")
async def wsBackupImageTask(websocket: WebSocket):
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

            await Backup.backupImageTask(fromId, toId, saveFolder)
            # 处理并响应数据
            await websocket.send_text(str(100))

        except Exception as e:
            print(f"Connection error: {e}")
            break


@app.get("/exportxlsxByDateTime/{start:str}/{end:str}")
async def exportxlsxByDateTime(start, end):
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
