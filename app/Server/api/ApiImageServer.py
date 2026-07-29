import asyncio
import io
import itertools
import logging
import os
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
from cachetools import cached
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse, Response

from Base.CONFIG import serverConfigProperty
from Base.tools.DataGet import DataGet, noFindImageByte
from cache import areaCache
from cache.area_tile_builder import DEFAULT_AREA_TILE_COUNT, rebuild_area_tile_cache
from cache.base import _resolve_image_path
from cache.bounded_cache import (MemoryBoundedTTLCache, memory_budget_bytes,
                                 positive_int_env)
from .api_core import app
from Base.tools.tool import expansion_box, bound_box

log = logging.getLogger(__name__)

router = APIRouter(tags=["图像访问服务"])

# 线程池用于IO密集型操作 - 根据 CPU 核心数动态调整
cpu_count = os.cpu_count() or 4


def _get_image_api_thread_workers() -> int:
    default_workers = min(max(cpu_count * 2, 4), 16)
    raw_workers = os.getenv("IMAGE_API_THREAD_POOL_WORKERS")
    if not raw_workers:
        return default_workers
    try:
        workers = int(raw_workers)
    except ValueError:
        log.warning("invalid IMAGE_API_THREAD_POOL_WORKERS=%s, use default=%s",
                    raw_workers, default_workers)
        return default_workers
    return min(max(workers, 1), 64)


_IMAGE_THREAD_WORKERS = _get_image_api_thread_workers()
thread_pool = ThreadPoolExecutor(max_workers=_IMAGE_THREAD_WORKERS,
                                 thread_name_prefix="image_api")
_IMAGE_MAX_INFLIGHT = positive_int_env("IMAGE_API_MAX_INFLIGHT",
                                       _IMAGE_THREAD_WORKERS * 2)
_image_inflight_semaphore = asyncio.Semaphore(_IMAGE_MAX_INFLIGHT)


def _positive_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return max(float(default), 0.1)
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return max(float(default), 0.1)
    return max(value, 0.1)


_IMAGE_ADMISSION_TIMEOUT = _positive_float_env(
    "IMAGE_API_ADMISSION_TIMEOUT", 10.0)
_IMAGE_OPERATION_TIMEOUT = _positive_float_env(
    "IMAGE_API_OPERATION_TIMEOUT", 60.0)
_IMAGE_HEALTH_STALL_SECONDS = _positive_float_env(
    "IMAGE_API_HEALTH_STALL_SECONDS", 90.0)
_DEFECT_CROP_MAX_DIMENSION = positive_int_env(
    "DEFECT_CROP_MAX_DIMENSION", 8192)
_DEFECT_CROP_MAX_PIXELS = positive_int_env(
    "DEFECT_CROP_MAX_PIXELS", 4 * 1024 * 1024)
_image_operation_ids = itertools.count(1)
_image_operations_lock = threading.Lock()
_image_operations: dict[int, dict[str, float | None]] = {}

# 预取开关 - 默认禁用以减少后台负载
ENABLE_PREFETCH = os.getenv("ENABLE_IMAGE_PREFETCH", "false").lower() == "true"
_MAX_PREFETCH_TASKS = positive_int_env("IMAGE_API_MAX_PREFETCH_TASKS", 8)
_prefetch_tasks: set[asyncio.Task] = set()

# 多级瓦片加载配置
# 瓦片等级定义：(目标尺寸, JPEG质量)
TILE_LEVELS = {
    0: (340, 60),  # Level 0: 1/16 缩略图 (~20KB)
    1: (682, 70),  # Level 1: 1/8 (~50KB)
    2: (1364, 80),  # Level 2: 1/4 (~120KB)
    3: (2728, 90),  # Level 3: 1/2 (~250KB)
    4: (5460, 95),  # Level 4: 原图瓦片 (~500KB)
}

# 默认原图瓦片尺寸（3x3切分时单个瓦片的大小）
DEFAULT_TILE_SIZE = 5460
AREA_IMAGE_TYPES = {"AREA", "AREA_MASK"}


def get_pool():
    return thread_pool


def _resolved_path(path: str) -> Path:
    return _resolve_image_path(path)


def _file_response(path: str,
                   media_type: str = "image/jpeg") -> Optional[FileResponse]:
    resolved = _resolved_path(path)
    if not resolved.exists():
        return None
    suffix = resolved.suffix.lower()
    if suffix == ".png":
        media_type = "image/png"
    elif suffix in {".jpg", ".jpeg"}:
        media_type = "image/jpeg"
    return FileResponse(resolved, media_type=media_type)


def _image_media_type(path: str, default: str = "image/jpeg") -> str:
    suffix = _resolved_path(path).suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return default


def _get_image_size_from_path(path: str) -> Optional[Tuple[int, int]]:
    resolved = _resolved_path(path)
    if not resolved.exists():
        return None
    try:
        with Image.open(resolved) as img:
            return img.size
    except Exception:
        log.debug("failed to read image size from %s", resolved, exc_info=True)
        return None


def _get_area_tile_cache_size(path: str,
                              tile_count: int) -> Optional[Tuple[int, int]]:
    """Read the legacy AREA tile dimensions away from the event loop."""
    try:
        cache_dir = areaCache._tile_cache_dir(path, 4)
        tile_path = cache_dir / "0_0.jpg"
        if not tile_path.exists():
            return None
        with Image.open(tile_path) as tile_img:
            tile_w, tile_h = tile_img.size
        if tile_w <= 0 or tile_h <= 0:
            return None
        return tile_w * tile_count, tile_h * tile_count
    except Exception:
        log.debug("failed to read AREA tile cache size: %s",
                  path,
                  exc_info=True)
        return None


def _render_area_tile_fallback(image_bytes: bytes, row: int, col: int,
                               count: int, level: int) -> Optional[bytes]:
    """Decode, crop and encode an AREA tile outside the event loop."""
    if count <= 0:
        return None

    np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)
    if image is None:
        return None

    height, width = image.shape[:2]
    tile_width = width // count
    tile_height = height // count
    if tile_width <= 0 or tile_height <= 0:
        return None

    x1 = col * tile_width
    y1 = row * tile_height
    x2 = width if col == count - 1 else x1 + tile_width
    y2 = height if row == count - 1 else y1 + tile_height
    tile = image[y1:y2, x1:x2]
    if tile.size == 0:
        return None

    target_size, quality = TILE_LEVELS[level]
    if level < 4 and (tile.shape[0] > target_size
                      or tile.shape[1] > target_size):
        scale = target_size / max(tile.shape[0], tile.shape[1])
        new_width = max(int(tile.shape[1] * scale), 1)
        new_height = max(int(tile.shape[0] * scale), 1)
        tile = cv2.resize(tile, (new_width, new_height),
                          interpolation=cv2.INTER_AREA)

    ok, buffer = cv2.imencode(".jpg", tile,
                              [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        return None
    return buffer.tobytes()


def _area_image_type(type_: str) -> str:
    type_ = str(type_ or "AREA").upper()
    if type_ not in AREA_IMAGE_TYPES:
        log.warning("unsupported AREA image type=%s, fallback to AREA", type_)
        return "AREA"
    return type_


async def _run_image_operation(operation):
    """Run an image operation with bounded executor admission.

    The semaphore is released by the executor future, rather than the request
    coroutine, so a disconnected/cancelled client cannot leave native image
    work accumulating in the executor's otherwise-unbounded queue.
    """
    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(_image_inflight_semaphore.acquire(),
                               timeout=_IMAGE_ADMISSION_TIMEOUT)
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=503,
                            detail="image service is busy") from exc

    operation_id = next(_image_operation_ids)
    with _image_operations_lock:
        _image_operations[operation_id] = {
            "submitted_at": time.monotonic(),
            "started_at": None,
        }

    def _tracked_operation():
        with _image_operations_lock:
            state = _image_operations.get(operation_id)
            if state is not None:
                state["started_at"] = time.monotonic()
        return operation()

    try:
        future = loop.run_in_executor(get_pool(), _tracked_operation)
    except Exception:
        with _image_operations_lock:
            _image_operations.pop(operation_id, None)
        _image_inflight_semaphore.release()
        raise

    def _release_slot(_future) -> None:
        with _image_operations_lock:
            _image_operations.pop(operation_id, None)
        try:
            loop.call_soon_threadsafe(_image_inflight_semaphore.release)
        except RuntimeError:
            # The application loop can already be closed during interpreter
            # shutdown.  There is no future work to admit in that case.
            _image_inflight_semaphore.release()

    future.add_done_callback(_release_slot)
    try:
        return await asyncio.wait_for(asyncio.shield(future),
                                      timeout=_IMAGE_OPERATION_TIMEOUT)
    except asyncio.TimeoutError as exc:
        log.error("image operation timed out after %.1fs; operation_id=%s",
                  _IMAGE_OPERATION_TIMEOUT, operation_id)
        raise HTTPException(status_code=504,
                            detail="image operation timed out") from exc


def _image_executor_health() -> dict:
    now = time.monotonic()
    with _image_operations_lock:
        operations = tuple(_image_operations.values())
    running_durations = [
        now - float(state["started_at"])
        for state in operations
        if state.get("started_at") is not None
    ]
    stalled_workers = sum(duration >= _IMAGE_HEALTH_STALL_SECONDS
                          for duration in running_durations)
    return {
        "ok": stalled_workers < _IMAGE_THREAD_WORKERS,
        "active": len(operations),
        "running": len(running_durations),
        "stalledWorkers": stalled_workers,
        "workers": _IMAGE_THREAD_WORKERS,
        "oldestRunningSeconds": round(max(running_durations, default=0.0),
                                      3),
    }


app.state.image_operation_health = _image_executor_health


async def _get_image_async(data_get: DataGet,
                           *,
                           pil: bool = False,
                           clip_num: int = 0):
    """将阻塞的磁盘/解码操作放入线程池，避免阻塞事件循环。"""
    return await _run_image_operation(
        lambda: data_get.get_image(pil=pil, clip_num=clip_num))


def _neighbor_ids(coil_id):
    try:
        cid = int(coil_id)
    except Exception:
        return []
    res = []
    if cid - 1 > 0:
        res.append(str(cid - 1))
    res.append(str(cid + 1))
    return res


def _schedule_prefetch(source_type: str,
                       surface_key: str,
                       coil_id,
                       type_: str,
                       *,
                       mask: bool = False,
                       clip_num: int = 0):
    """预加载相邻卷的同类型图像以加速切换。可通过环境变量 ENABLE_IMAGE_PREFETCH 启用。"""
    if not ENABLE_PREFETCH:
        return
    if len(_prefetch_tasks) >= _MAX_PREFETCH_TASKS:
        return

    neighbors = _neighbor_ids(coil_id)
    if not neighbors:
        return
    loop = asyncio.get_running_loop()

    for nid in neighbors:
        data_get = DataGet(source_type, surface_key, nid, type_, mask)

        async def _prefetch(dg=data_get, nid_=nid):
            try:
                await _get_image_async(dg, clip_num=clip_num)
            except Exception:
                log.debug("prefetch failed %s %s %s",
                          source_type,
                          nid_,
                          type_,
                          exc_info=True)

        if len(_prefetch_tasks) >= _MAX_PREFETCH_TASKS:
            break
        task = loop.create_task(_prefetch())
        _prefetch_tasks.add(task)
        task.add_done_callback(_prefetch_tasks.discard)


@router.get("/image/preview/{surface_key:str}/{coil_id:str}/{type_:str}")
async def get_preview_image(surface_key,
                            coil_id: str,
                            type_: str,
                            mask: bool = False):
    try:
        data_get = DataGet("preview", surface_key, coil_id, type_, mask)
        image_bytes = await _get_image_async(data_get)
        _schedule_prefetch("preview", surface_key, coil_id, type_, mask=mask)
        media_type = _image_media_type(
            data_get.url) if image_bytes else "image/jpeg"
        return Response(image_bytes or noFindImageByte,
                        media_type=media_type,
                        headers={"Cache-Control": "public, max-age=600"})
    except Exception as e:
        log.exception("preview error")
        return Response(content=noFindImageByte, media_type="image/jpeg")


@router.get("/image/source/{surface_key:str}/{coil_id:str}/{type_:str}")
async def get_image(surface_key,
                    coil_id: str,
                    type_: str,
                    mask: bool = False,
                    thumbnail: bool = False):
    """
    增加 2D 影像
    """
    if thumbnail:
        return await get_preview_image(surface_key, coil_id, type_, mask=mask)

    data_get = DataGet("source", surface_key, coil_id, type_, mask)
    file_response = await _run_image_operation(
        lambda: _file_response(data_get.url))
    if file_response is not None:
        _schedule_prefetch("source", surface_key, coil_id, type_, mask=mask)
        return file_response
    image_bytes = await _get_image_async(data_get)
    if image_bytes is None:
        return Response(content=noFindImageByte, media_type="image/jpeg")
    _schedule_prefetch("source", surface_key, coil_id, type_, mask=mask)
    return Response(image_bytes, media_type="image/jpeg")


@router.post(
    "/image/area/cache/rebuild/{surface_key:str}/{coil_id:str}/{type_:str}")
async def rebuild_area_tile_cache_api(surface_key: str,
                                      coil_id: str,
                                      type_: str = "AREA"):
    type_ = _area_image_type(type_)
    data_get = DataGet("source", surface_key, coil_id, type_, False)
    result = await _run_image_operation(
        lambda: rebuild_area_tile_cache(data_get.url,
                                        tile_count=DEFAULT_AREA_TILE_COUNT,
                                        remove_existing=True),
    )
    if not result.rebuilt:
        raise HTTPException(status_code=404,
                            detail=result.error
                            or "AREA image tile cache rebuild failed")

    await _run_image_operation(areaCache.clear_cache)
    payload = result.to_dict()
    payload.update({
        "surface_key": surface_key,
        "coil_id": coil_id,
        "type": type_,
    })
    log.info(
        "rebuilt AREA tile cache surface=%s coil=%s type=%s image=%s cache=%s tiles=%s removed=%s",
        surface_key, coil_id, type_, payload["image_path"],
        payload["cache_dir"], payload["tiles"], payload["removed_files"])
    return payload


@router.post("/image/area/cache/clear")
async def clear_area_tile_memory_cache_api():
    await _run_image_operation(areaCache.clear_cache)
    log.info("cleared AREA tile memory cache")
    return {"ok": True}


@router.get("/image/area/{surface_key:str}/{coil_id:str}/{type_:str}")
@router.get("/image/area/{surface_key:str}/{coil_id:str}")
async def get_area_tiled(surface_key: str,
                         coil_id: str,
                         type_: str = "AREA",
                         row: int = Query(0, ge=-2, le=2, description="瓦片行索引"),
                         col: int = Query(0, ge=0, le=2, description="瓦片列索引"),
                         count: int = Query(0, ge=0, le=3,
                                            description="瓦片行列数"),
                         level: int = Query(4,
                                            ge=0,
                                            le=4,
                                            description="瓦片质量等级 0-4")):
    """
    多级瓦片加载接口

    参数说明:
    - row=-1: 返回完整图像
    - row=-2: 返回预览图像
    - count=0: 返回图像宽高信息
    - level: 瓦片质量等级 (0=缩略图 1/16, 1=1/8, 2=1/4, 3=1/2, 4=原图)

    瓦片等级:
    - Level 0: 340x340, JPEG 60 (~20KB)
    - Level 1: 682x682, JPEG 70 (~50KB)
    - Level 2: 1364x1364, JPEG 80 (~120KB)
    - Level 3: 2728x2728, JPEG 90 (~250KB)
    - Level 4: 5460x5460, JPEG 95 (~500KB)

    缓存策略:
    - 优先从缓存读取对应级别的瓦片（直接返回，速度最快）
    - 缓存不存在时，生成所有级别的瓦片并保存
    """
    row = int(row)
    col = int(col)
    count = int(count)
    level = int(level)
    type_ = _area_image_type(type_)
    requested_count = count
    tile_count = DEFAULT_AREA_TILE_COUNT
    data_get = DataGet("source", surface_key, coil_id, type_, False)

    if count > 0:
        count = tile_count

    # 处理预览图像请求
    if row == -2:
        preview_get = DataGet("preview", surface_key, coil_id, type_, False)
        image_bytes = await _get_image_async(preview_get)
        _schedule_prefetch("preview", surface_key, coil_id, type_, mask=False)
        return Response(image_bytes or noFindImageByte,
                        media_type="image/jpeg")

    # 返回完整图像
    if row == -1:
        image_bytes = await _get_image_async(data_get)
        _schedule_prefetch("source", surface_key, coil_id, type_, mask=False)
        return Response(image_bytes or noFindImageByte,
                        media_type="image/jpeg")

    if requested_count == 1:
        image_bytes = await _get_image_async(data_get)
        _schedule_prefetch("source", surface_key, coil_id, type_, mask=False)
        return Response(image_bytes or noFindImageByte,
                        media_type="image/jpeg")

    # 返回图像宽高信息
    if count == 0:
        size = await _run_image_operation(
            lambda: _get_image_size_from_path(data_get.url))
        if size is not None:
            w, h = size
            _schedule_prefetch("source",
                               surface_key,
                               coil_id,
                               type_,
                               mask=False,
                               clip_num=tile_count)
            return {"width": w, "height": h}

        # 缓存只作为旧数据兜底；优先使用真实原图尺寸，避免最后一行/列余数被 0_0 tile * 3 吃掉。
        cached_size = await _run_image_operation(
            lambda: _get_area_tile_cache_size(data_get.url, tile_count))
        if cached_size is not None:
            return {"width": cached_size[0], "height": cached_size[1]}

        return Response(content=noFindImageByte, media_type="image/jpeg")

    # ========== 核心逻辑：优先从缓存读取指定级别的瓦片 ==========
    # 1. 尝试从缓存直接读取对应级别的瓦片（最快）
    tile_bytes = await _run_image_operation(
        lambda: areaCache.get_tile(data_get.url, row, col, count, level))
    if tile_bytes:
        # 缓存命中，直接返回
        if row == 0 and col == 0:
            _schedule_prefetch("source",
                               surface_key,
                               coil_id,
                               type_,
                               mask=False,
                               clip_num=tile_count)
        return Response(tile_bytes,
                        media_type="image/jpeg",
                        headers={
                            "X-Tile-Level": str(level),
                            "X-Cache": "hit"
                        })

    # 2. 缓存未命中，回退到原来的实时生成模式
    log.info("Cache miss L%s (%s,%s), falling back to real-time generation",
             level, col, row)

    # 获取所有瓦片（会触发多级缓存生成）
    image_dict = await _get_image_async(data_get, clip_num=count)
    if image_dict:
        try:
            crop_image_byte = image_dict[col][row]

            # 如果不是最高等级，需要调整尺寸
            if level < 4:
                crop_image_byte = await _run_image_operation(
                    lambda: _resize_tile(crop_image_byte,
                                         TILE_LEVELS[level][0],
                                         TILE_LEVELS[level][1]))

            if row == 0 and col == 0:
                _schedule_prefetch("source",
                                   surface_key,
                                   coil_id,
                                   type_,
                                   mask=False,
                                   clip_num=tile_count)

            return Response(crop_image_byte,
                            media_type="image/jpeg",
                            headers={
                                "X-Tile-Level": str(level),
                                "X-Cache": "miss"
                            })
        except Exception:
            log.debug(
                "failed to read generated AREA tile: %s row=%s col=%s count=%s level=%s",
                data_get.url,
                row,
                col,
                count,
                level,
                exc_info=True)
            return Response(content=noFindImageByte, media_type="image/jpeg")

    # 3. 从原始图像切分（最后的备选方案）
    image_bytes = await _get_image_async(data_get)
    if image_bytes is None:
        return Response(content=noFindImageByte, media_type="image/jpeg")

    crop_image_byte = await _run_image_operation(
        lambda: _render_area_tile_fallback(image_bytes, row, col, count,
                                           level))
    if crop_image_byte is None:
        return Response(content=noFindImageByte, media_type="image/jpeg")

    if row == 0 and col == 0:
        _schedule_prefetch("source",
                           surface_key,
                           coil_id,
                           type_,
                           mask=False,
                           clip_num=tile_count)

    return Response(crop_image_byte,
                    media_type="image/jpeg",
                    headers={
                        "X-Tile-Level": str(level),
                        "X-Cache": "fallback"
                    })


def _resize_tile(tile_bytes: bytes, target_size: int, quality: int) -> bytes:
    """
    调整瓦片尺寸

    Args:
        tile_bytes: 原始瓦片字节数据
        target_size: 目标尺寸（长边）
        quality: JPEG质量

    Returns:
        调整后的瓦片字节数据
    """
    try:
        np_arr = np.frombuffer(tile_bytes, dtype=np.uint8)
        tile = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)

        if tile is None:
            log.warning(
                "Resize failed: imdecode returned None, target_size=%s",
                target_size)
            return tile_bytes

        # 计算缩放比例
        original_size = max(tile.shape[0], tile.shape[1])
        if original_size <= 0:
            log.warning("Resize failed: empty tile, target_size=%s",
                        target_size)
            return tile_bytes
        scale = target_size / original_size

        if scale >= 1.0:
            # 不需要缩小，直接返回（略微降低质量以减小文件）
            ok, buf = cv2.imencode(".jpg", tile,
                                   [cv2.IMWRITE_JPEG_QUALITY, quality])
            result = buf.tobytes() if ok else tile_bytes
            log.debug(
                "Resize: scale=%.2f>=1.0, no resize needed, returning %s bytes",
                scale,
                len(result),
            )
            return result

        # 缩小图像
        new_w = int(tile.shape[1] * scale)
        new_h = int(tile.shape[0] * scale)
        resized = cv2.resize(tile, (new_w, new_h),
                             interpolation=cv2.INTER_AREA)

        # 编码
        ok, buf = cv2.imencode(".jpg", resized,
                               [cv2.IMWRITE_JPEG_QUALITY, quality])
        result = buf.tobytes() if ok else tile_bytes
        if ok:
            log.debug(
                "Resize: %s -> (%s,%s), %s bytes at quality=%s",
                tile.shape,
                new_w,
                new_h,
                len(result),
                quality,
            )
        else:
            log.warning("Resize: imencode failed for resized image (%s,%s)",
                        new_w, new_h)
        return result

    except Exception as e:
        log.error("Failed to resize tile: %s", e, exc_info=True)
        return tile_bytes


_DETECTION_CANDIDATE_CACHE = MemoryBoundedTTLCache(
    max_bytes=memory_budget_bytes("DETECTION_CANDIDATE_CACHE_MAX_MB", 32),
    max_entries=positive_int_env("DETECTION_CANDIDATE_CACHE_MAX_ITEMS", 128),
    ttl=positive_int_env("DETECTION_CANDIDATE_CACHE_TTL", 300),
)
_DETECTION_CANDIDATE_CACHE_LOCK = threading.RLock()
_MAX_DETECTION_CANDIDATES = positive_int_env(
    "MAX_DETECTION_CANDIDATES_PER_COIL", 10000)


@cached(cache=_DETECTION_CANDIDATE_CACHE,
        lock=_DETECTION_CANDIDATE_CACHE_LOCK)
def _load_detection_candidates(
        coil_id: int) -> Tuple[Tuple[int, int, int, int, str], ...]:
    candidates = []
    save_folder = list(
        serverConfigProperty.surfaceConfigPropertyDict.values())[0].saveFolder
    save_base = Path(save_folder).parent
    detection_folder = save_base / str(coil_id) / "detection"

    if not detection_folder.exists():
        return tuple()

    for defect_type_folder in detection_folder.iterdir():
        if not defect_type_folder.is_dir():
            continue

        for xml_file in defect_type_folder.glob("*.xml"):
            png_file = xml_file.with_suffix(".png")
            if not png_file.exists():
                continue
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                for obj in root.findall("object"):
                    bbox = obj.find("bndbox")
                    if bbox is None:
                        continue
                    candidates.append((
                        int(bbox.find("xmin").text),
                        int(bbox.find("ymin").text),
                        int(bbox.find("xmax").text),
                        int(bbox.find("ymax").text),
                        str(png_file),
                    ))
                    if len(candidates) >= _MAX_DETECTION_CANDIDATES:
                        log.warning(
                            "detection candidates truncated coil=%s limit=%s",
                            coil_id,
                            _MAX_DETECTION_CANDIDATES,
                        )
                        return tuple(candidates)
            except Exception:
                log.debug("Error parsing XML %s", xml_file, exc_info=True)

    return tuple(candidates)


def _get_defect_image_from_detection(coil_id: int, surface_key: str, x: int,
                                     y: int, w: int, h: int) -> Optional[Path]:
    try:
        requested_center_x = x + w / 2
        requested_center_y = y + h / 2

        for xml_xmin, xml_ymin, xml_xmax, xml_ymax, png_path in _load_detection_candidates(
                coil_id):
            if xml_xmin <= requested_center_x <= xml_xmax and xml_ymin <= requested_center_y <= xml_ymax:
                path = Path(png_path)
                if path.exists():
                    return path

        log.debug(
            "No matching defect image found in detection folder for coil %s",
            coil_id)
        return None

    except Exception as e:
        log.debug("Error reading from detection folder: %s", e)
        return None


def _image_cache_key(path: str) -> Optional[Tuple[int, int]]:
    try:
        stat = _resolved_path(path).stat()
        return stat.st_mtime_ns, stat.st_size
    except OSError:
        return None


_DEFECT_CROP_CACHE = MemoryBoundedTTLCache(
    max_bytes=memory_budget_bytes("DEFECT_CROP_CACHE_MAX_MB", 64),
    max_entries=positive_int_env("DEFECT_CROP_CACHE_MAX_ITEMS", 256),
    ttl=positive_int_env("DEFECT_CROP_CACHE_TTL", 300),
)
_DEFECT_CROP_CACHE_LOCK = threading.RLock()


@cached(cache=_DEFECT_CROP_CACHE, lock=_DEFECT_CROP_CACHE_LOCK)
def _crop_defect_image_cached(
    surface_key: str,
    coil_id: int,
    type_: str,
    x: int,
    y: int,
    w: int,
    h: int,
    mtime_ns: int,
    file_size: int,
) -> Optional[bytes]:
    image = DataGet("image", surface_key, coil_id, type_,
                    False).get_image(pil=True)
    if image is None:
        return None

    img_w, img_h = image.size
    old_box = [x, y, w, h]

    if x < 0:
        w += x
        x = 0
    if y < 0:
        h += y
        y = 0
    if x >= img_w:
        x = img_w - 1
    if y >= img_h:
        y = img_h - 1
    if x + w > img_w:
        w = img_w - x
    if y + h > img_h:
        h = img_h - y
    if w <= 0:
        w = 1
    if h <= 0:
        h = 1

    crop_image = image.crop((x, y, x + w, y + h))
    try:
        with io.BytesIO() as img_byte_arr:
            if bound_box([x, y, w, h], image.size):
                new_image = Image.new(crop_image.mode,
                                      (old_box[2], old_box[3]), (0, 0, 0))
                try:
                    paste_x_y = (int((old_box[2] - w) / 2),
                                 int((old_box[3] - h) / 2))
                    new_image.paste(crop_image, paste_x_y)
                    new_image.save(img_byte_arr, format="jpeg", quality=85)
                finally:
                    new_image.close()
            else:
                crop_image.save(img_byte_arr, format="jpeg", quality=85)
            return img_byte_arr.getvalue()
    finally:
        crop_image.close()


async def _shutdown_image_api_resources() -> None:
    tasks = tuple(_prefetch_tasks)
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    _prefetch_tasks.clear()
    with _DEFECT_CROP_CACHE_LOCK:
        _DEFECT_CROP_CACHE.clear()
    with _DETECTION_CANDIDATE_CACHE_LOCK:
        _DETECTION_CANDIDATE_CACHE.clear()
    with _image_operations_lock:
        _image_operations.clear()
    thread_pool.shutdown(wait=False, cancel_futures=True)


app.add_event_handler("shutdown", _shutdown_image_api_resources)


@router.get(
    "/defect_image/{surface_key:str}/{coil_id:int}/{type_:str}/{x:str}/{y:str}/{w:str}/{h:str}"
)
async def get_defect_image(surface_key, coil_id: int, type_: str, x: str,
                           y: str, w: str, h: str):
    # 处理 NaN 或无效值
    try:
        x = int(x) if x and x.lower() != 'nan' else 0
        y = int(y) if y and y.lower() != 'nan' else 0
        w = int(w) if w and w.lower() != 'nan' else 100
        h = int(h) if h and h.lower() != 'nan' else 100
    except (ValueError, TypeError):
        return Response(noFindImageByte, media_type="image/jpeg")

    if w <= 0 or h <= 0:
        return Response(noFindImageByte, media_type="image/jpeg")
    if (w > _DEFECT_CROP_MAX_DIMENSION
            or h > _DEFECT_CROP_MAX_DIMENSION
            or w * h > _DEFECT_CROP_MAX_PIXELS):
        raise HTTPException(status_code=413,
                            detail="requested defect crop is too large")

    detection_image = await _run_image_operation(
        lambda: _get_defect_image_from_detection(coil_id, surface_key, x, y,
                                                  w, h))
    if detection_image is not None:
        return FileResponse(detection_image, media_type="image/png")

    data_get = DataGet("image", surface_key, coil_id, type_, False)
    cache_key = await _run_image_operation(
        lambda: _image_cache_key(data_get.url))
    if cache_key is None:
        return Response(noFindImageByte, media_type="image/jpeg")

    crop_bytes = await _run_image_operation(
        lambda: _crop_defect_image_cached(surface_key, coil_id, type_, x, y, w,
                                          h, cache_key[0], cache_key[1]),
    )
    if crop_bytes is None:
        return Response(noFindImageByte, media_type="image/jpeg")

    return Response(
        content=crop_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=300"},
    )


# 注册路由
app.include_router(router)
