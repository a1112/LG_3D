import datetime
import json
from typing import Optional, Dict

from fastapi import WebSocket, APIRouter
from fastapi.responses import StreamingResponse

from CoilDataBase import backup

from CONFIG import serverConfigProperty
from utils import Backup, export
from .Models import ExportXlsxConfigModel
from .api_core import app

router = APIRouter(tags=["备份服务"])


@router.get("/save_to_sql/{sql_file:path}")
def save_to_sql(sql_file: str):
    state=False
    if ".sql" in sql_file.lower():
        state = backup.backup_to_sql(sql_file, mysqldump_exe=serverConfigProperty.mysqldump_exe)
    if ".db" in sql_file.lower():
        state = backup.backup_to_sqlite(sql_file)
    return {"state": state}

@router.websocket("/ws/backupImageTask")
async def ws_backup_image_task(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            # 接收客户端发送的消息
            data = await websocket.receive_text()
            data = json.loads(data)
            from_id = data['from_id']
            to_id = data['to_id']
            save_folder = data['folder']

            async def msgFunc_(value):
                await websocket.send_text(str(value))

            await Backup.backup_image_task(from_id, to_id, save_folder)
            # 处理并响应数据
            await websocket.send_text(str(100))

        except Exception as e:
            print(f"Connection error: {e}")
            break




@router.get("/exportXlsxById/{start:int}/{end:int}")
async def export_xlsx_by_id(start, end,export_type = "3D", export_config = None ):
    output, file_size = export.export_data_by_coil_id(start, end,export_type=export_type, export_config=export_config)
    headers = {
        "Content-Disposition": f"attachment; filename=example.xlsx",
        "Content-Length": str(file_size)  # 设置文件大小
    }

    # 将 BytesIO 对象传递给 StreamingResponse，设置内容类型和附件名称
    response = StreamingResponse(output, headers=headers,
                                 media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    return response



@router.get("/exportXlsxByDateTime/{start:str}/{end:str}")
async def export_xlsx_by_datetime(start, end,export_type = "3D", export_config = None ):
    """
    根据时间导出数据 %Y%m%d%H%M : 202401100100
    :param start: 开始时间
    :param end: 结束时间
    :param export_type: 导出类型
    :param export_config:
    :return:
    """
    start = datetime.datetime.strptime(start, "%Y%m%d%H%M")
    end = datetime.datetime.strptime(end, "%Y%m%d%H%M")
    output, file_size = export.export_data_by_time(
        start, end,export_type=export_type,export_config = export_config
    )

    headers = {
        "Content-Disposition": f"attachment; filename=example.xlsx",
        "Content-Length": str(file_size)  # 设置文件大小
    }

    # 将 BytesIO 对象传递给 StreamingResponse，设置内容类型和附件名称
    response = StreamingResponse(output, headers=headers,
                                 media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    return response


@router.post("/export_xlsx")
async def export_xlsx_post(export_xlsx_config:ExportXlsxConfigModel ):
    print(export_xlsx_config)
    # config = ExportXlsxConfigModel(data)
    # {'export_type': 'xlsx', 'detection_3d_info': True, 'defect_info': True, 'defect_show_info': True,
    #  'defect_un_show_info': False, 'startDate': '202502140929', 'endDate': '202502140929'}
    start = datetime.datetime.strptime(export_xlsx_config.startDate, "%Y%m%d%H%M")
    end = datetime.datetime.strptime(export_xlsx_config.endDate, "%Y%m%d%H%M")
    output, file_size = export.export_data_by_time(
        start, end, export_config=export_xlsx_config
    )

    headers = {
        "Content-Disposition": f"attachment; filename=example.xlsx",
        "Content-Length": str(file_size)  # 设置文件大小
    }

    # 将 BytesIO 对象传递给 StreamingResponse，设置内容类型和附件名称
    response = StreamingResponse(output, headers=headers,
                                 media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    return response

app.include_router(router)
