import datetime
import json
import traceback

from fastapi import APIRouter, WebSocket
from fastapi.responses import PlainTextResponse, StreamingResponse

from CoilDataBase import backup

from Base.CONFIG import serverConfigProperty
from Base.utils import Backup, export
from .Models import ExportXlsxConfigModel
from .api_core import app

router = APIRouter(tags=["备份服务"])


def _stream_xlsx(output, file_size: int, filename: str) -> StreamingResponse:
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Length": str(file_size),
    }
    return StreamingResponse(
        output,
        headers=headers,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _export_error_response(exc: Exception) -> PlainTextResponse:
    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    print(detail)
    return PlainTextResponse(detail, status_code=500)


@router.get("/save_to_sql/{sql_file:path}")
def save_to_sql(sql_file: str):
    state = False
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
            data = json.loads(await websocket.receive_text())
            from_id = data["from_id"]
            to_id = data["to_id"]
            save_folder = data["folder"]
            await Backup.backup_image_task(from_id, to_id, save_folder)
            await websocket.send_text("100")
        except Exception as exc:
            print(f"Connection error: {exc}")
            break


@router.get("/exportXlsxById/{start:int}/{end:int}")
async def export_xlsx_by_id(start, end, export_type="3D", export_config=None):
    try:
        output, file_size = export.export_data_by_coil_id(
            start,
            end,
            export_type=export_type,
            export_config=export_config,
        )
        return _stream_xlsx(output, file_size, "example.xlsx")
    except Exception as exc:
        return _export_error_response(exc)


@router.get("/exportXlsxByDateTime/{start:str}/{end:str}")
async def export_xlsx_by_datetime(start, end, export_type="3D", export_config=None):
    try:
        start_dt = datetime.datetime.strptime(start, "%Y%m%d%H%M")
        end_dt = datetime.datetime.strptime(end, "%Y%m%d%H%M")
        output, file_size = export.export_data_by_time(
            start_dt,
            end_dt,
            export_type=export_type,
            export_config=export_config,
        )
        return _stream_xlsx(output, file_size, "example.xlsx")
    except Exception as exc:
        return _export_error_response(exc)


@router.post("/export_xlsx")
async def export_xlsx_post(export_xlsx_config: ExportXlsxConfigModel):
    try:
        print(export_xlsx_config)
        start_dt = datetime.datetime.strptime(export_xlsx_config.startDate, "%Y%m%d%H%M")
        end_dt = datetime.datetime.strptime(export_xlsx_config.endDate, "%Y%m%d%H%M")
        output, file_size = export.export_data_by_time(
            start_dt,
            end_dt,
            export_config=export_xlsx_config,
        )
        return _stream_xlsx(output, file_size, "example.xlsx")
    except Exception as exc:
        return _export_error_response(exc)


@router.get("/export_1h")
async def export_last_1h():
    try:
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(hours=1)
        export_config = ExportXlsxConfigModel(
            startDate=start_time.strftime("%Y%m%d%H%M"),
            endDate=end_time.strftime("%Y%m%d%H%M"),
            export_type="3D",
            detection_3d_info=True,
            defect_info=True,
            defect_show_info=True,
            defect_un_show_info=False,
            export_plc_data=False,
        )
        output, file_size = export.export_data_by_time(
            start_time,
            end_time,
            export_config=export_config,
        )
        filename = f"export_1h_{start_time.strftime('%Y%m%d_%H%M')}.xlsx"
        return _stream_xlsx(output, file_size, filename)
    except Exception as exc:
        return _export_error_response(exc)


@router.post("/export_1h")
async def export_last_1h_post():
    return await export_last_1h()


@router.get("/export_24h")
async def export_last_24h():
    try:
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(hours=24)
        export_config = ExportXlsxConfigModel(
            startDate=start_time.strftime("%Y%m%d%H%M"),
            endDate=end_time.strftime("%Y%m%d%H%M"),
            export_type="3D",
            detection_3d_info=True,
            defect_info=True,
            defect_show_info=True,
            defect_un_show_info=False,
            export_plc_data=False,
        )
        output, file_size = export.export_data_by_time(
            start_time,
            end_time,
            export_config=export_config,
        )
        filename = f"export_24h_{start_time.strftime('%Y%m%d_%H%M')}.xlsx"
        return _stream_xlsx(output, file_size, filename)
    except Exception as exc:
        return _export_error_response(exc)


@router.post("/export_24h")
async def export_last_24h_post():
    return await export_last_24h()


@router.get("/export_today")
async def export_today():
    try:
        end_time = datetime.datetime.now()
        start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        export_config = ExportXlsxConfigModel(
            startDate=start_time.strftime("%Y%m%d%H%M"),
            endDate=end_time.strftime("%Y%m%d%H%M"),
            export_type="3D",
            detection_3d_info=True,
            defect_info=True,
            defect_show_info=True,
            defect_un_show_info=False,
            export_plc_data=False,
        )
        output, file_size = export.export_data_by_time(
            start_time,
            end_time,
            export_config=export_config,
        )
        filename = f"export_today_{start_time.strftime('%Y%m%d')}.xlsx"
        return _stream_xlsx(output, file_size, filename)
    except Exception as exc:
        return _export_error_response(exc)


@router.post("/export_today")
async def export_today_post():
    return await export_today()


app.include_router(router)
