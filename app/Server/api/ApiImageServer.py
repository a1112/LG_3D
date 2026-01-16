import asyncio
import io
import logging
import time
from pathlib import Path
from typing import List

import cv2
import numpy as np
from PIL import Image
from fastapi import APIRouter
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
async def get_area_tiled(surface_key: str, coil_id: str, row=0, col=0, count=0):
    """
    并发处理图像分块请求
    row == -1 返回完整图像
    count == 0 返回宽高
    按照 count 分割返回图像
    """
    row = int(row)
    col = int(col)
    count = int(count)
    tile_count = 3
    if count > 0:
        count = tile_count

    if count == 1:
        return None
    if row == -2:
        data_get = DataGet("preview", surface_key, coil_id, "AREA", False)
        image_bytes = await _get_image_async(data_get)
        _schedule_prefetch("preview", surface_key, coil_id, "AREA", mask=False)
        return Response(image_bytes or noFindImageByte, media_type="image/jpeg")

    data_get = DataGet("source", surface_key, coil_id, "AREA", False)

    # 返回完整图像
    if row == -1:
        image_bytes = await _get_image_async(data_get)
        _schedule_prefetch("source", surface_key, coil_id, "AREA", mask=False)
        return Response(image_bytes or noFindImageByte, media_type="image/jpeg")

    if count == 0:
        try:
            cache_dir = areaCache._tile_cache_dir(data_get.url)
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

    image_dict = await _get_image_async(data_get, clip_num=count)
    if image_dict:
        try:
            crop_image_byte = image_dict[col][row]
            if row == 0 and col == 0:
                _schedule_prefetch("source", surface_key, coil_id, "AREA", mask=False, clip_num=tile_count)
            return Response(crop_image_byte, media_type="image/jpg")
        except Exception:
            return Response(content=noFindImageByte, media_type="image/jpeg")

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
    x1 = row * w_width
    y1 = col * h_height
    x2 = x1 + w_width
    y2 = y1 + h_height
    tile = image[y1:y2, x1:x2]
    ok, buf = cv2.imencode(".jpg", tile)
    if not ok:
        return Response(content=noFindImageByte, media_type="image/jpeg")
    crop_image_byte = buf.tobytes()
    if row == 0 and col == 0:
        _schedule_prefetch("source", surface_key, coil_id, "AREA", mask=False, clip_num=tile_count)
    return Response(crop_image_byte, media_type="image/jpg")  # 注意修改为正确的MIME类型


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
