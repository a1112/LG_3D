import asyncio
import inspect
import math
import os
from pathlib import Path
import shutil
from concurrent.futures import ThreadPoolExecutor

from Base.CONFIG import serverConfigProperty
from .Zip import compress_camera_data_once


try:
    BACKUP_IMAGE_WORKERS = max(
        1, int(os.getenv("LG3D_BACKUP_IMAGE_WORKERS", "2")))
except ValueError:
    BACKUP_IMAGE_WORKERS = 2

try:
    BACKUP_IMAGE_CONCURRENCY = max(
        1, int(os.getenv("LG3D_BACKUP_IMAGE_CONCURRENCY", "1")))
except ValueError:
    BACKUP_IMAGE_CONCURRENCY = 1

try:
    BACKUP_IMAGE_MAX_COILS = max(
        1, int(os.getenv("LG3D_BACKUP_IMAGE_MAX_COILS", "500")))
except ValueError:
    BACKUP_IMAGE_MAX_COILS = 500

try:
    BACKUP_IMAGE_ADMISSION_TIMEOUT = float(
        os.getenv("LG3D_BACKUP_IMAGE_ADMISSION_TIMEOUT", "2"))
    if (not math.isfinite(BACKUP_IMAGE_ADMISSION_TIMEOUT)
            or BACKUP_IMAGE_ADMISSION_TIMEOUT <= 0):
        BACKUP_IMAGE_ADMISSION_TIMEOUT = 2.0
except (TypeError, ValueError, OverflowError):
    BACKUP_IMAGE_ADMISSION_TIMEOUT = 2.0

_backup_semaphore = asyncio.Semaphore(BACKUP_IMAGE_CONCURRENCY)


class BackupRangeLimitExceeded(ValueError):
    """Raised before starting an image backup with an unsafe ID range."""

    def __init__(self, max_coils: int):
        self.max_coils = max_coils
        super().__init__(f"backup range exceeds {max_coils} coils")


class BackupBusyError(RuntimeError):
    """Raised when a running filesystem backup already owns capacity."""


def _configured_source_folders():
    seen = set()
    folders = []
    for surface in serverConfigProperty.surfaceConfigPropertyDict.values():
        for folder in surface.folderList:
            source = Path(folder["source"])
            source_key = str(source.resolve())
            if source_key in seen:
                continue
            seen.add(source_key)
            folders.append(source)
    return folders


def _backup_source_folder(source, from_id, to_id, save_folder):
    destination_root = save_folder / source.name
    copied = 0
    missing = 0
    for coil_id in range(from_id, to_id):
        source_folder = source / str(coil_id)
        if not source_folder.exists():
            missing += 1
            continue
        shutil.copytree(
            source_folder,
            destination_root / str(coil_id),
            dirs_exist_ok=True,
        )
        copied += 1
    compressed = compress_camera_data_once(
        destination_root,
        reserve_num=0,
        require_quiet=False,
    )
    return copied, missing, compressed


def _backup_image_sync(from_id, to_id, save_folder):
    save_folder.mkdir(exist_ok=True, parents=True)
    source_folders = _configured_source_folders()
    totals = {
        "sourceFolders": len(source_folders),
        "copiedFolders": 0,
        "missingFolders": 0,
        "compressedFolders": 0,
    }
    with ThreadPoolExecutor(max_workers=BACKUP_IMAGE_WORKERS) as executor:
        futures = [
            executor.submit(
                _backup_source_folder,
                source,
                from_id,
                to_id,
                save_folder,
            )
            for source in source_folders
        ]
        for future in futures:
            copied, missing, compressed = future.result()
            totals["copiedFolders"] += copied
            totals["missingFolders"] += missing
            totals["compressedFolders"] += compressed
    return totals


async def backup_image_task(from_id: int,
                            to_id: int,
                            save_folder: str,
                            msg_func=None):
    from_id = int(from_id)
    to_id = int(to_id)
    if to_id <= from_id:
        raise ValueError("to_id must be greater than from_id")
    if to_id - from_id > BACKUP_IMAGE_MAX_COILS:
        raise BackupRangeLimitExceeded(BACKUP_IMAGE_MAX_COILS)

    try:
        await asyncio.wait_for(
            _backup_semaphore.acquire(),
            timeout=BACKUP_IMAGE_ADMISSION_TIMEOUT,
        )
    except asyncio.TimeoutError as exc:
        raise BackupBusyError("image backup capacity is busy") from exc
    loop = asyncio.get_running_loop()
    try:
        future = loop.run_in_executor(
            None,
            _backup_image_sync,
            from_id,
            to_id,
            Path(save_folder),
        )
    except Exception:
        _backup_semaphore.release()
        raise

    try:
        result = await asyncio.shield(future)
    except asyncio.CancelledError:

        def _release_cancelled_backup(completed_future) -> None:
            try:
                completed_future.exception()
            except (asyncio.CancelledError, Exception):
                pass
            finally:
                try:
                    loop.call_soon_threadsafe(_backup_semaphore.release)
                except RuntimeError:
                    _backup_semaphore.release()

        # The filesystem copy cannot be cancelled safely. Keep its admission
        # slot occupied until the worker really exits so disconnect storms do
        # not accumulate unbounded backup jobs in the default executor.
        future.add_done_callback(_release_cancelled_backup)
        raise
    except Exception:
        _backup_semaphore.release()
        raise
    else:
        _backup_semaphore.release()
    if msg_func:
        callback_result = msg_func(100)
        if inspect.isawaitable(callback_result):
            await callback_result
    return result
