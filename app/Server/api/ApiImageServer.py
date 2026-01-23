import asyncio
import io
import logging
import time
from pathlib import Path
from typing import List

import cv2
import numpy as np
from PIL import Image
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse, FileResponse, Response

from Base.tools.DataGet import DataGet, noFindImageByte
from cache import areaCache
from .api_core import app
from Base.tools.tool import expansion_box, bound_box

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

router = APIRouter(tags=["图像访问服务"])

# 线程池用于IO密集型操作
thread_pool = ThreadPoolExecutor(max_workers=10)
log = logging.getLogger(__name__)

# 多级瓦片加载配置
# 瓦片等级定义：size为瓦片目标尺寸，quality为JPEG质量(1-100)
TILE_LEVELS = {
    0: {"size": 340, "quality": 60},    # Level 0: 1/16 缩略图 (~20KB)
    1: {"size": 682, "quality": 70},    # Level 1: 1/8 (~50KB)
    2: {"size": 1364, "quality": 80},   # Level 2: 1/4 (~120KB)
    3: {"size": 2728, "quality": 90},   # Level 3: 1/2 (~250KB)
    4: {"size": 5460, "quality": 95},   # Level 4: 原图瓦片 (~500KB)
}

# 默认原图瓦片尺寸（3x3切分时单个瓦片的大小）
DEFAULT_TILE_SIZE = 5460


def get_pool():
    return thread_pool


async def _get_image_async(data_get: DataGet, *, pil: bool = False, clip_num: int = 0):
    """将阻塞的磁盘/解码操作放入线程池，避免阻塞事件循环。"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(get_pool(), lambda: data_get.get_image(pil=pil, clip_num=clip_num))


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


def _schedule_prefetch(source_type: str, surface_key: str, coil_id, type_: str, *, mask: bool = False, clip_num: int = 0):
    """预加载相邻卷的同类型图像以加速切换。"""
    neighbors = _neighbor_ids(coil_id)
    if not neighbors:
        return
    loop = asyncio.get_event_loop()

    for nid in neighbors:
        data_get = DataGet(source_type, surface_key, nid, type_, mask)

        async def _prefetch(dg=data_get, nid_=nid):
            try:
                await _get_image_async(dg, clip_num=clip_num)
            except Exception:
                log.debug("prefetch failed %s %s %s", source_type, nid_, type_, exc_info=True)

        loop.create_task(_prefetch())


@router.get("/image/preview/{surface_key:str}/{coil_id:str}/{type_:str}")
async def get_preview_image(surface_key, coil_id: str, type_: str, mask: bool = False):
    try:
        data_get = DataGet("preview", surface_key, coil_id, type_, mask)
        image_bytes = await _get_image_async(data_get)
        _schedule_prefetch("preview", surface_key, coil_id, type_, mask=mask)
        return Response(image_bytes, media_type="image/jpeg")
    except Exception as e:
        log.exception("preview error")
        return Response(content=noFindImageByte, media_type="image/jpeg")


@router.get("/image/source/{surface_key:str}/{coil_id:str}/{type_:str}")
async def get_image(surface_key, coil_id: str, type_: str, mask: bool = False):
    """
    增加 2D 影像
    """
    data_get = DataGet("source", surface_key, coil_id, type_, mask)
    image_bytes = await _get_image_async(data_get)
    if image_bytes is None:
        return Response(content=noFindImageByte, media_type="image/jpeg")
    _schedule_prefetch("source", surface_key, coil_id, type_, mask=mask)
    return Response(image_bytes, media_type="image/jpeg")


@router.get("/image/area/{surface_key:str}/{coil_id:str}")
async def get_area_tiled(
    surface_key: str,
    coil_id: str,
    row: int = Query(0, ge=-2, le=2, description="瓦片行索引"),
    col: int = Query(0, ge=0, le=2, description="瓦片列索引"),
    count: int = Query(0, ge=0, le=3, description="瓦片行列数"),
    level: int = Query(4, ge=0, le=4, description="瓦片质量等级 0-4")
):
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
    tile_count = 3

    if count > 0:
        count = tile_count

    if count == 1:
        return None

    data_get = DataGet("source", surface_key, coil_id, "AREA", False)

    # 处理预览图像请求
    if row == -2:
        preview_get = DataGet("preview", surface_key, coil_id, "AREA", False)
        image_bytes = await _get_image_async(preview_get)
        _schedule_prefetch("preview", surface_key, coil_id, "AREA", mask=False)
        return Response(image_bytes or noFindImageByte, media_type="image/jpeg")

    # 返回完整图像
    if row == -1:
        image_bytes = await _get_image_async(data_get)
        _schedule_prefetch("source", surface_key, coil_id, "AREA", mask=False)
        return Response(image_bytes or noFindImageByte, media_type="image/jpeg")

    # 返回图像宽高信息
    if count == 0:
        try:
            # 尝试从 L4 缓存获取尺寸
            cache_dir = areaCache._tile_cache_dir(data_get.url, 4)
            tile_path = cache_dir / "0_0.jpg"
            if tile_path.exists():
                with Image.open(tile_path) as tile_img:
                    tile_w, tile_h = tile_img.size
                if tile_w > 0 and tile_h > 0:
                    return {"width": tile_w * tile_count, "height": tile_h * tile_count}
        except Exception:
            pass

        image_bytes = await _get_image_async(data_get)
        if image_bytes is None:
            return Response(content=noFindImageByte, media_type="image/jpeg")
        loop = asyncio.get_event_loop()

        def _calc_wh():
            np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
            image = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)
            if image is None:
                return None
            h, w = image.shape[:2]
            return h, w

        size = await loop.run_in_executor(get_pool(), _calc_wh)
        if size is None:
            return Response(content=noFindImageByte, media_type="image/jpeg")
        h, w = size
        _schedule_prefetch("source", surface_key, coil_id, "AREA", mask=False, clip_num=tile_count)
        return {"width": w, "height": h}

    # ========== 核心逻辑：优先从缓存读取指定级别的瓦片 ==========
    # 1. 尝试从缓存直接读取对应级别的瓦片（最快）
    tile_bytes = areaCache.get_tile(data_get.url, row, col, count, level)
    if tile_bytes:
        # 缓存命中，直接返回
        if row == 0 and col == 0:
            _schedule_prefetch("source", surface_key, coil_id, "AREA", mask=False, clip_num=tile_count)
        return Response(
            tile_bytes,
            media_type="image/jpeg",
            headers={
                "X-Tile-Level": str(level),
                "X-Cache": "hit"
            }
        )

    # 2. 缓存未命中，回退到原来的实时生成模式
    log.info(f"Cache miss L{level} ({col},{row}), falling back to real-time generation")

    # 获取所有瓦片（会触发多级缓存生成）
    image_dict = await _get_image_async(data_get, clip_num=count)
    if image_dict:
        try:
            crop_image_byte = image_dict[col][row]

            # 如果不是最高等级，需要调整尺寸
            if level < 4:
                crop_image_byte = _resize_tile(crop_image_byte, TILE_LEVELS[level][0], TILE_LEVELS[level][1])

            if row == 0 and col == 0:
                _schedule_prefetch("source", surface_key, coil_id, "AREA", mask=False, clip_num=tile_count)

            return Response(
                crop_image_byte,
                media_type="image/jpeg",
                headers={
                    "X-Tile-Level": str(level),
                    "X-Cache": "miss"
                }
            )
        except Exception:
            return Response(content=noFindImageByte, media_type="image/jpeg")

    # 3. 从原始图像切分（最后的备选方案）
    image_bytes = await _get_image_async(data_get)
    if image_bytes is None:
        return Response(content=noFindImageByte, media_type="image/jpeg")

    np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)
    if image is None:
        return Response(content=noFindImageByte, media_type="image/jpeg")

    h, w = image.shape[:2]
    w_width = w // count
    h_height = h // count

    if w_width <= 0 or h_height <= 0:
        return Response(content=noFindImageByte, media_type="image/jpeg")

    # 切分瓦片
    x1 = row * w_width
    y1 = col * h_height
    x2 = x1 + w_width
    y2 = y1 + h_height
    tile = image[y1:y2, x1:x2]

    # 根据等级调整尺寸和质量
    target_size, quality = TILE_LEVELS[level]
    if level < 4 and (tile.shape[0] > target_size or tile.shape[1] > target_size):
        scale = target_size / max(tile.shape[0], tile.shape[1])
        new_w = int(tile.shape[1] * scale)
        new_h = int(tile.shape[0] * scale)
        tile = cv2.resize(tile, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # 编码为JPEG
    ok, buf = cv2.imencode(".jpg", tile, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        return Response(content=noFindImageByte, media_type="image/jpeg")

    crop_image_byte = buf.tobytes()

    if row == 0 and col == 0:
        _schedule_prefetch("source", surface_key, coil_id, "AREA", mask=False, clip_num=tile_count)

    return Response(
        crop_image_byte,
        media_type="image/jpeg",
        headers={
            "X-Tile-Level": str(level),
            "X-Cache": "fallback"
        }
    )


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
            log.warning(f"Resize failed: imdecode returned None, target_size={target_size}")
            return tile_bytes

        # 计算缩放比例
        original_size = max(tile.shape[0], tile.shape[1])
        scale = target_size / original_size

        if scale >= 1.0:
            # 不需要缩小，直接返回（略微降低质量以减小文件）
            ok, buf = cv2.imencode(".jpg", tile, [cv2.IMWRITE_JPEG_QUALITY, quality])
            result = buf.tobytes() if ok else tile_bytes
            log.debug(f"Resize: scale={scale:.2f}>=1.0, no resize needed, returning {len(result)} bytes")
            return result

        # 缩小图像
        new_w = int(tile.shape[1] * scale)
        new_h = int(tile.shape[0] * scale)
        resized = cv2.resize(tile, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # 编码
        ok, buf = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, quality])
        result = buf.tobytes() if ok else tile_bytes
        if ok:
            log.debug(f"Resize: {tile.shape} -> ({new_w},{new_h}), {len(result)} bytes at quality={quality}")
        else:
            log.warning(f"Resize: imencode failed for resized image ({new_w},{new_h})")
        return result

    except Exception as e:
        log.error(f"Failed to resize tile: {e}", exc_info=True)
        return tile_bytes


@router.get("/defect_image/{surface_key:str}/{coil_id:int}/{type_:str}/{x:str}/{y:str}/{w:str}/{h:str}")
async def get_defect_image(surface_key, coil_id: int, type_: str, x: str, y: str, w: str, h: str):
    x, y, w, h = int(x), int(y), int(w), int(h)
    old_box = [x, y, w, h]
    image = DataGet("image", surface_key, coil_id, type_, False).get_image(pil=True)
    image: Image.Image
    if image is None:
        return Response(noFindImageByte, media_type="image/jpeg")

    x, y, w, h = expansion_box([x, y, w, h], image.size, expand_factor=0)
    crop_image = image.crop((x, y, x + w, y + h))
    img_byte_arr = io.BytesIO()

    if bound_box([x, y, w, h], image.size):
        new_image = Image.new(crop_image.mode, (old_box[2], old_box[3]), (0, 0, 0))
        paste_x_y = (int((old_box[2] - w) / 2), int((old_box[3] - h) / 2))
        new_image.paste(crop_image, paste_x_y)
        new_image.paste(crop_image, paste_x_y)
        new_image.save(img_byte_arr, format='jpeg')
    else:
        crop_image.save(img_byte_arr, format='jpeg')
    img_byte_arr.seek(0)

    return Response(content=img_byte_arr.getvalue(), media_type="image/jpeg")


# 注册路由
app.include_router(router)
