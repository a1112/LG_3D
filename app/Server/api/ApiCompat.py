import asyncio
import logging
import math
from io import BytesIO
from pathlib import Path
import os

import xlsxwriter
from fastapi import APIRouter, HTTPException
from fastapi.openapi.docs import get_swagger_ui_oauth2_redirect_html
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from starlette.background import BackgroundTask

from CoilDataBase import Coil
from Base.utils import export
from .api_core import app

router = APIRouter(tags=["兼容服务"])
logger = logging.getLogger(__name__)
_simple_export_semaphore = asyncio.Semaphore(1)


def _positive_float_env(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError, OverflowError):
        return default
    return value if math.isfinite(value) and value > 0 else default


_SIMPLE_EXPORT_ADMISSION_TIMEOUT = _positive_float_env(
    "SIMPLE_EXPORT_ADMISSION_TIMEOUT", 2.0)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _software_update_package_path() -> Path | None:
    package_env = _env("RUST_API_SOFTWARE_UPDATE_PACKAGE_FILE")
    if not package_env:
        return None

    package_path = Path(package_env)
    if not package_path.is_file():
        return None
    return package_path


def _sanitize_download_file_name(file_name: str) -> str:
    return Path(file_name).name.replace("\r", "").replace("\n", "")


def _is_plain_download_file_name(file_name: str) -> bool:
    sanitized = _sanitize_download_file_name(file_name)
    return bool(file_name) and sanitized == file_name and "/" not in file_name and "\\" not in file_name and not any(
        ord(ch) < 32 for ch in file_name
    )


async def _close_simple_export_response(output: BytesIO) -> None:
    try:
        output.close()
    finally:
        _simple_export_semaphore.release()


def _stream_xlsx(output: BytesIO, file_size: int, filename: str) -> StreamingResponse:
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Length": str(file_size),
    }
    try:
        return StreamingResponse(
            output,
            headers=headers,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            background=BackgroundTask(_close_simple_export_response, output),
        )
    except Exception:
        output.close()
        _simple_export_semaphore.release()
        raise


def _export_error_response(exc: Exception) -> PlainTextResponse:
    if isinstance(exc, HTTPException):
        return PlainTextResponse(str(exc.detail), status_code=exc.status_code)
    if isinstance(exc, export.ExportDefectLimitExceeded):
        logger.warning("exportDataSimple rejected: %s", exc)
        return PlainTextResponse(str(exc), status_code=413)
    logger.exception("exportDataSimple failed: %s", exc)
    return PlainTextResponse("export xlsx failed", status_code=500)


@router.get("/docs/oauth2-redirect.html", include_in_schema=False)
async def docs_oauth2_redirect_html():
    return get_swagger_ui_oauth2_redirect_html()


@router.get("/software_update/manifest")
async def software_update_manifest():
    package_path = await asyncio.to_thread(_software_update_package_path)
    package_file_name = package_path.name if package_path else ""
    version = _env("RUST_API_SOFTWARE_UPDATE_VERSION", "0.1.1")
    download_url = _env("RUST_API_SOFTWARE_UPDATE_URL")

    if not download_url and package_file_name:
        download_url = f"/updates/{package_file_name}"
    file_name = _env("RUST_API_SOFTWARE_UPDATE_FILE_NAME", package_file_name)
    release_notes = _env("RUST_API_SOFTWARE_UPDATE_NOTES")

    return {
        "version": version,
        "latest_version": version,
        "current_version": "0.1.1",
        "download_url": download_url,
        "downloadUrl": download_url,
        "package_url": download_url,
        "packageUrl": download_url,
        "file_name": file_name,
        "fileName": file_name,
        "release_notes": release_notes,
        "releaseNotes": release_notes,
        "notes": release_notes,
    }


@router.get("/updates/{file_name}")
async def updates(file_name: str):
    package_path = await asyncio.to_thread(_software_update_package_path)
    if package_path is None:
        return PlainTextResponse("file not found", status_code=404)

    if not _is_plain_download_file_name(file_name):
        return PlainTextResponse("file not found", status_code=404)

    if package_path.name != file_name:
        return PlainTextResponse("file not found", status_code=404)

    return FileResponse(package_path, media_type="application/octet-stream", filename=file_name)


@router.get("/exportDataSimple")
async def export_data_simple():
    output = None
    try:
        try:
            await asyncio.wait_for(
                _simple_export_semaphore.acquire(),
                timeout=_SIMPLE_EXPORT_ADMISSION_TIMEOUT,
            )
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=503,
                detail="simple export capacity is busy",
            ) from exc
        loop = asyncio.get_running_loop()
        try:
            future = loop.run_in_executor(None, _build_simple_export)
        except Exception:
            _simple_export_semaphore.release()
            raise
        try:
            output = await asyncio.shield(future)
        except asyncio.CancelledError:

            def _cleanup_cancelled_export(completed_future) -> None:
                try:
                    completed_output = completed_future.result()
                    completed_output.close()
                except Exception:
                    pass
                finally:
                    _simple_export_semaphore.release()

            future.add_done_callback(_cleanup_cancelled_export)
            raise
        except Exception:
            _simple_export_semaphore.release()
            raise
        return _stream_xlsx(output, output.getbuffer().nbytes, "exportDataSimple.xlsx")
    except Exception as exc:
        return _export_error_response(exc)


def _build_simple_export() -> BytesIO:
    output = BytesIO()
    try:
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        try:
            secondary_coil_list = Coil.get_all_join_data_by_num(
                50,
                max_defects=export.DEFAULT_MAX_EXPORT_DEFECTS,
            )
        except Coil.QueryDefectLimitExceeded as exc:
            raise export.ExportDefectLimitExceeded(
                export.DEFAULT_MAX_EXPORT_DEFECTS) from exc
        export.export_data_by_coil_id_list(secondary_coil_list,
                                           workbook,
                                           export_type="3D")
        workbook.close()
        output.seek(0)
        return output
    except Exception:
        output.close()
        raise


app.include_router(router)
