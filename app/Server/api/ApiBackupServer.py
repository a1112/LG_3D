import asyncio
import datetime
import json
import logging
import math
import os
from functools import partial

from fastapi import APIRouter, HTTPException, WebSocket
from fastapi.responses import PlainTextResponse, StreamingResponse
from starlette.background import BackgroundTask

from CoilDataBase import backup

from Base.CONFIG import serverConfigProperty
from Base.utils import Backup, export
from .Models import ExportXlsxConfigModel
from .api_core import app

logger = logging.getLogger(__name__)

try:
    _EXPORT_CONCURRENCY = max(1, int(os.getenv("REPORT_EXPORT_CONCURRENCY", "1")))
except ValueError:
    _EXPORT_CONCURRENCY = 1
    logger.warning("invalid REPORT_EXPORT_CONCURRENCY; falling back to 1")
_export_semaphore = asyncio.Semaphore(_EXPORT_CONCURRENCY)


def _positive_int_env(name: str, default: int) -> int:
    try:
        return max(int(os.getenv(name, str(default))), 1)
    except ValueError:
        logger.warning("invalid %s, use default %s", name, default)
        return default


def _positive_float_env(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError, OverflowError):
        logger.warning("invalid %s, use default %s", name, default)
        return default
    if not math.isfinite(value) or value <= 0:
        logger.warning("invalid %s, use default %s", name, default)
        return default
    return value


# These limits protect the in-memory XLSX builder, but they must also cover a
# normal production day.  The old 500/500 defaults rejected /export_24h as
# soon as the selected coils had more than 500 defects and surfaced in Qt as
# the misleading "Request Entity Too Large" download error.
_EXPORT_MAX_COILS = _positive_int_env("REPORT_EXPORT_MAX_COILS", 5000)
_EXPORT_MAX_DEFECTS = _positive_int_env("REPORT_EXPORT_MAX_DEFECTS", 20000)
_EXPORT_MAX_DAYS = _positive_int_env("REPORT_EXPORT_MAX_DAYS", 31)
_EXPORT_ADMISSION_TIMEOUT = _positive_float_env(
    "REPORT_EXPORT_ADMISSION_TIMEOUT", 2.0)

router = APIRouter(tags=["备份服务"])


def _validate_export_id_range(start: int, end: int) -> None:
    if end < start:
        raise HTTPException(status_code=400,
                            detail="export end id must not precede start id")
    if end - start + 1 > _EXPORT_MAX_COILS:
        raise HTTPException(
            status_code=413,
            detail=f"export range exceeds {_EXPORT_MAX_COILS} coils",
        )


def _validate_export_time_range(start: datetime.datetime,
                                end: datetime.datetime) -> None:
    if end < start:
        raise HTTPException(
            status_code=400,
            detail="export end time must not precede start time",
        )
    if end - start > datetime.timedelta(days=_EXPORT_MAX_DAYS):
        raise HTTPException(
            status_code=413,
            detail=f"export range exceeds {_EXPORT_MAX_DAYS} days",
        )


async def _close_export_response(output) -> None:
    try:
        output.close()
    finally:
        _export_semaphore.release()


def _stream_xlsx(output, file_size: int, filename: str) -> StreamingResponse:
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Length": str(file_size),
    }
    try:
        return StreamingResponse(
            output,
            headers=headers,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            background=BackgroundTask(_close_export_response, output),
        )
    except Exception:
        output.close()
        _export_semaphore.release()
        raise


async def _run_export(export_function, *args, **kwargs):
    """Run CPU/IO-heavy workbook generation without blocking the API loop.

    Workbook exports are deliberately bounded because each job holds its complete
    XLSX payload in memory. Queuing excess requests is substantially safer than
    allowing several large exports to exhaust memory at the same time.
    """
    try:
        await asyncio.wait_for(_export_semaphore.acquire(),
                               timeout=_EXPORT_ADMISSION_TIMEOUT)
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=503,
                            detail="report export capacity is busy") from exc
    loop = asyncio.get_running_loop()
    try:
        future = loop.run_in_executor(
            None, partial(export_function, *args, **kwargs))
    except Exception:
        _export_semaphore.release()
        raise
    try:
        return await asyncio.shield(future)
    except asyncio.CancelledError:

        def _cleanup_cancelled_export(completed_future) -> None:
            try:
                result = completed_future.result()
                output = result[0] if isinstance(result, tuple) else result
                close = getattr(output, "close", None)
                if callable(close):
                    close()
            except Exception:
                pass
            finally:
                _export_semaphore.release()

        future.add_done_callback(_cleanup_cancelled_export)
        raise
    except Exception:
        _export_semaphore.release()
        raise


def _export_error_response(exc: Exception) -> PlainTextResponse:
    if isinstance(exc, HTTPException):
        return PlainTextResponse(str(exc.detail), status_code=exc.status_code)
    if isinstance(exc, (export.ExportLimitExceeded,
                        export.ExportDefectLimitExceeded)):
        logger.warning("export xlsx rejected: %s", exc)
        return PlainTextResponse(str(exc), status_code=413)
    logger.exception("export xlsx failed: %s", exc)
    return PlainTextResponse("export xlsx failed", status_code=500)


@router.get("/save_to_sql/{sql_file:path}")
def save_to_sql(sql_file: str):
    state = False
    if ".sql" in sql_file.lower():
        state = backup.backup_to_sql(
            sql_file,
            mysqldump_exe=serverConfigProperty.mysqldump_exe,
            pg_dump_exe=serverConfigProperty.pg_dump_exe,
        )
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
            logger.warning("backup image websocket closed after error: %s", exc)
            break


@router.get("/exportXlsxById/{start:int}/{end:int}")
async def export_xlsx_by_id(start, end, export_type="3D", export_config=None):
    _validate_export_id_range(int(start), int(end))
    try:
        output, file_size = await _run_export(
            export.export_data_by_coil_id,
            start,
            end,
            export_type=export_type,
            export_config=export_config,
            max_defects=_EXPORT_MAX_DEFECTS,
        )
        return _stream_xlsx(output, file_size, "example.xlsx")
    except Exception as exc:
        return _export_error_response(exc)


@router.get("/exportXlsxByDateTime/{start:str}/{end:str}")
async def export_xlsx_by_datetime(start, end, export_type="3D", export_config=None):
    try:
        start_dt = datetime.datetime.strptime(start, "%Y%m%d%H%M")
        end_dt = datetime.datetime.strptime(end, "%Y%m%d%H%M")
        _validate_export_time_range(start_dt, end_dt)
        output, file_size = await _run_export(
            export.export_data_by_time,
            start_dt,
            end_dt,
            export_type=export_type,
            export_config=export_config,
            max_coils=_EXPORT_MAX_COILS,
            max_defects=_EXPORT_MAX_DEFECTS,
        )
        return _stream_xlsx(output, file_size, "example.xlsx")
    except HTTPException:
        raise
    except Exception as exc:
        return _export_error_response(exc)


@router.post("/export_xlsx")
async def export_xlsx_post(export_xlsx_config: ExportXlsxConfigModel):
    try:
        logger.info("export xlsx requested: %s", export_xlsx_config)
        start_dt = datetime.datetime.strptime(export_xlsx_config.startDate, "%Y%m%d%H%M")
        end_dt = datetime.datetime.strptime(export_xlsx_config.endDate, "%Y%m%d%H%M")
        _validate_export_time_range(start_dt, end_dt)
        output, file_size = await _run_export(
            export.export_data_by_time,
            start_dt,
            end_dt,
            export_config=export_xlsx_config,
            max_coils=_EXPORT_MAX_COILS,
            max_defects=_EXPORT_MAX_DEFECTS,
        )
        return _stream_xlsx(output, file_size, "example.xlsx")
    except HTTPException:
        raise
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
        output, file_size = await _run_export(
            export.export_data_by_time,
            start_time,
            end_time,
            export_config=export_config,
            max_coils=_EXPORT_MAX_COILS,
            max_defects=_EXPORT_MAX_DEFECTS,
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
        output, file_size = await _run_export(
            export.export_data_by_time,
            start_time,
            end_time,
            export_config=export_config,
            max_coils=_EXPORT_MAX_COILS,
            max_defects=_EXPORT_MAX_DEFECTS,
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
        output, file_size = await _run_export(
            export.export_data_by_time,
            start_time,
            end_time,
            export_config=export_config,
            max_coils=_EXPORT_MAX_COILS,
            max_defects=_EXPORT_MAX_DEFECTS,
        )
        filename = f"export_today_{start_time.strftime('%Y%m%d')}.xlsx"
        return _stream_xlsx(output, file_size, filename)
    except Exception as exc:
        return _export_error_response(exc)


@router.post("/export_today")
async def export_today_post():
    return await export_today()


app.include_router(router)
