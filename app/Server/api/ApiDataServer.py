import io
import logging
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from fastapi import APIRouter, Query, WebSocket
from fastapi.responses import FileResponse, Response
from starlette.responses import StreamingResponse

from Base.property.Data3D import LineData
from Base.property.Types import Point2D
from Base.tools.DataGet import DataGet, noFindImageByte
from Base.CONFIG import serverConfigProperty
from ._tool_ import get_bool
from .api_core import app
from cache import cacheProvider

router = APIRouter(tags=["深度数据访问服务"])
log = logging.getLogger(__name__)


@router.get("/coilData/heightData/{surface_key:str}/{coil_id:str}")
async def get_height_data(surface_key, coil_id: str, x1: int = 0, y1: int = 0, x2: int = 0, y2: int = 0):
    """
    Return line segments for curve display.

    The UI expects:
    [
      {
        "pointL": [x0, y0],
        "pointR": [x1, y1],
        "points": [[x, y, z], ...]
      },
      ...
    ]
    """
    data_get = DataGet("image", surface_key, coil_id, "MASK", False)
    mask_image = data_get.get_image(pil=True)
    npy_data = data_get.get_3d_data()

    if mask_image is None or npy_data is None:
        return []

    mask_image = np.array(mask_image)
    if not y2 and not x2:
        x2, y2 = x1 + 10, y1

    line_data = LineData(npy_data, mask_image, Point2D(x1, y1), Point2D(x2, y2))
    segments = line_data.split_image_line_points()

    result = []
    for seg in segments:
        if not seg:
            continue
        # seg is a list/array of [x, y, z]
        left = seg[0]
        right = seg[-1]
        result.append(
            {
                "pointL": [int(left[0]), int(left[1])],
                "pointR": [int(right[0]), int(right[1])],
                "points": [[int(p[0]), int(p[1]), int(p[2])] for p in seg],
            }
        )
    return result


@router.get("/coilData/heightPoint/{surface_key:str}/{coil_id:str}")
async def get_height_point(surface_key, coil_id: str, x: int = 0, y: int = 0):

    data_get = DataGet("image", surface_key, coil_id, "MASK", False)
    npy_data = data_get.get_3d_data()
    try:
        print(int(npy_data[int(y)][int(x)]))
        return int(npy_data[int(y)][int(x)])
    except (BaseException,) as e:
        print(e)
        return "error"


@router.websocket("/ws/coilData/heightPoint")
async def ws_height_point(websocket: WebSocket):
    """
    WebSocket interface for querying single height points.

    Expected JSON message:
    {"id": 1, "surface_key": "S", "coil_id": "1755", "x": 100, "y": 200}
    """
    await websocket.accept()
    while True:
        message = await websocket.receive_json()
        req_id = message.get("id")
        surface_key = message.get("surface_key") or message.get("surfaceKey")
        coil_id = str(message.get("coil_id") or message.get("coilId") or "")
        x = int(message.get("x", 0))
        y = int(message.get("y", 0))

        base_resp = {"id": req_id, "surface_key": surface_key, "coil_id": coil_id, "x": x, "y": y}

        if not surface_key or not coil_id:
            await websocket.send_json({**base_resp, "error": "surface_key and coil_id are required"})
            continue

        data_get = DataGet("image", surface_key, coil_id, "MASK", False)
        npy_data = data_get.get_3d_data()
        try:
            value = int(npy_data[int(y)][int(x)])
            await websocket.send_json({**base_resp, "value": value})
        except Exception as exc:  # pragma: no cover - runtime guard
            await websocket.send_json({**base_resp, "error": str(exc)})


@router.get("/coilData/Render/{surfaceKey:str}/{coil_id:str}")
async def getRender(
    surfaceKey: str,
    coil_id: str,
    scale: float = Query(1.0, description="缩放比例"),
    mask: bool = Query(True, description="是否应用掩码"),
    min_value: int = Query(0, description="最小值"),
    max_value: int = Query(255, description="最大值"),
    thumbnail: bool = Query(False, description="是否返回缩略图（1024x1024）"),
    grayscale: bool = Query(False, description="是否使用灰度模式（GRAY）而非伪彩色（JET）"),
) -> Response:
    """
    获取渲染图像（支持伪彩色 JET 和灰度 GRAY）

    参数:
    - thumbnail=true: 返回缓存的缩略图（快速加载）
    - thumbnail=false: 返回完整渲染图像
    - grayscale=true: 返回灰度图像（GRAY.jpg 缓存）
    - grayscale=false: 返回伪彩色图像（JET.jpg 缓存）
    """
    mask = get_bool(mask)
    scale = float(scale)
    min_value = int(min_value)
    max_value = int(max_value)

    data_get = DataGet("image", surfaceKey, coil_id, "MASK", False)
    npy_data = data_get.get_3d_data()

    if npy_data is None:
        return Response(content=noFindImageByte, media_type="image/jpeg")

    # 选择颜色映射
    colormap = -1 if grayscale else cv2.COLORMAP_JET
    colormap_name = "GRAY" if grayscale else "JET"

    # ========== 缩略图模式（优先从缓存读取）==========
    if thumbnail:
        s_t = time.time()
        mask_array = None
        if mask:
            mask_image = data_get.get_image()
            if mask_image:
                mask_array = np.array(Image.open(io.BytesIO(mask_image)))

        # 尝试从缓存获取或生成缩略图
        if cacheProvider.falsecolor_cache:
            thumb_data, from_cache = cacheProvider.falsecolor_cache.get_or_generate(
                data_get.url,
                npy_data,
                mask_array,
                colormap,
                min_value,
                max_value
            )
            if thumb_data:
                log.info(f"Thumbnail ({colormap_name}): {'from cache' if from_cache else 'generated'} in {time.time()-s_t:.3f}s")
                return Response(thumb_data, media_type="image/jpeg", headers={
                    "X-Thumbnail": "true",
                    "X-From-Cache": str(from_cache),
                    "X-Colormap": colormap_name
                })

    # ========== 完整渲染模式 ==========
    s_t = time.time()
    mask_image = data_get.get_image()
    if mask_image:
        mask_image = Image.open(io.BytesIO(mask_image))
        mask_image = np.array(mask_image)

    r_size = (int(npy_data.shape[1] * scale), int(npy_data.shape[0] * scale))
    clip_npy = np.clip(npy_data, min_value, max_value)
    clip_npy = (clip_npy - min_value) / (max_value - min_value) * 255
    clip_npy = clip_npy.astype(np.uint8)

    if scale < 0.99:
        clip_npy = cv2.resize(clip_npy, r_size)
        if mask_image is not None and mask_image.size:
            mask_image = cv2.resize(mask_image, r_size)

    # 根据模式选择输出
    if grayscale:
        # GRAY 模式：转换为 BGR 以便 JPEG 编码
        rendered_image = cv2.cvtColor(clip_npy, cv2.COLOR_GRAY2BGR)
    else:
        # JET 模式：应用伪彩色
        rendered_image = cv2.applyColorMap(clip_npy, cv2.COLORMAP_JET)

    if mask and mask_image is not None:
        if grayscale:
            # GRAY 模式掩码需要 3 通道
            mask_3ch = cv2.merge([mask_image, mask_image, mask_image])
            rendered_image = cv2.bitwise_and(rendered_image, rendered_image, mask=mask_3ch)
        else:
            rendered_image = cv2.bitwise_and(rendered_image, rendered_image, mask=mask_image)

    _, img_encoded = cv2.imencode('.jpg', rendered_image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    img_bytes = img_encoded.tobytes()

    log.info(f"Full render ({colormap_name}): {time.time()-s_t:.3f}s")
    return Response(img_bytes, media_type="image/jpeg", headers={
        "X-Thumbnail": "false",
        "X-Colormap": colormap_name
    })


@router.get("/coilData/Area/{surface_key:str}/{coil_id:str}")
async def get_area(surface_key, coil_id: str, scale=1, mask: bool = True, valueFrom=0, valueTo=255, r=255, g=0, b=0):
    mask = get_bool(mask)
    scale = float(scale)
    min_value, max_value = int(valueFrom), int(valueTo)
    s_t = time.time()
    # 数据获取
    data_get = DataGet("image", surface_key, coil_id, "MASK", mask)
    npy_data = data_get.get_3d_data()
    mask_image = Image.open(io.BytesIO(data_get.get_mask_source()))
    # 数据处理
    mask_image = np.array(mask_image)
    rSize = (int(npy_data.shape[1] * scale), int(npy_data.shape[0] * scale))
    if scale < 0.99:
        npy_data = cv2.resize(npy_data, rSize, interpolation=cv2.INTER_AREA)
        mask_image = cv2.resize(mask_image, rSize, interpolation=cv2.INTER_AREA)
    height, width = npy_data.shape
    output_image = np.zeros((height, width, 4), dtype=np.uint8)  # BGRA 格式 透明
    color = [int(b), int(g), int(r), 255]
    # 蓝色区域
    output_image[(npy_data > min_value) & (npy_data < max_value)] = color  # B, G, R, A
    _, img_encoded = cv2.imencode('.png', output_image)
    img_bytes = io.BytesIO(img_encoded.tobytes())
    eT = time.time()
    print(f"Processing Time: {eT - s_t:.2f} seconds")
    # return StreamingResponse(img_bytes, media_type="image/png")


def _clip_box(x: int, y: int, w: int, h: int, img_w: int, img_h: int):
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(img_w, x + w)
    y2 = min(img_h, y + h)
    if x2 <= x1 or y2 <= y1:
        return None
    return x1, y1, x2, y2


@router.get("/classifier_image/{coil_id:int}/{surface_key:str}/{class_name:str}/{x:int}/{y:int}/{w:int}/{h:int}")
async def get_classifier_image(coil_id: int, surface_key: str, class_name: str, x: int, y: int, w: int, h: int):
    try:
        image_path = Path(serverConfigProperty.get_classifier_image(coil_id, surface_key, class_name, x, y, w, h))
        if image_path.exists():
            return FileResponse(image_path, media_type="image/png")
    except Exception:
        image_path = None

    data_get = DataGet("image", surface_key, str(coil_id), "GRAY", False)
    image = data_get.get_image(pil=True)
    if image is None:
        return Response(content=noFindImageByte, media_type="image/jpeg")

    box = _clip_box(x, y, w, h, image.size[0], image.size[1])
    if box is None:
        return Response(content=noFindImageByte, media_type="image/jpeg")
    crop_image = image.crop(box)
    img_byte_arr = io.BytesIO()
    crop_image.save(img_byte_arr, format="JPEG")
    img_byte_arr.seek(0)
    return Response(content=img_byte_arr.getvalue(), media_type="image/jpeg")


@router.get("/coilData/Error/{surface_key:str}/{coil_id:str}")
async def get_error(
        surface_key: str,
        coil_id: str,
        scale: float = 1.0,
        mask: bool = True,
        minValue: int = 0,
        maxValue: int = 255,
        force_cache: bool = False  # 强制使用缓存，如果缓存不存在则返回空白
):
    """
    获取 Error 塔形报警图像

    计算方法（与预生成缓存一致）：
    - 蓝色：低于 中位数 - minValue mm（塔形过小，远离侧）
    - 红色：高于 中位数 + maxValue mm（塔形过大，靠近侧）

    优先从 AlgServer 预生成的缓存读取 (png/Error.png)
    如果缓存不存在且 force_cache=False，则动态生成
    """
    mask = get_bool(mask)
    scale = float(scale)
    threshold_down_mm = int(minValue)
    threshold_up_mm = int(maxValue)
    sT = time.time()

    # ========== 优先读取预生成的缓存 ==========
    try:
        data_get = DataGet("source", surface_key, coil_id, "AREA", False)
        image_path = data_get.url  # 获取图像路径

        # 构造 Error.png 路径: {saveFolder}/{surface_key}/{coil_id}/png/Error.png
        from pathlib import Path
        path_obj = Path(image_path)
        if path_obj.parent.name in {"jpg", "png"}:
            coil_dir = path_obj.parent.parent
        else:
            coil_dir = path_obj.parent

        error_cache_path = coil_dir / "png" / "Error.png"

        if error_cache_path.exists():
            # 读取缓存的 Error.png
            with open(error_cache_path, "rb") as f:
                img_bytes = f.read()
            e_t = time.time()
            print(f"Error cache hit: {e_t - sT:.3f}s")
            return Response(content=img_bytes, media_type="image/png")

    except Exception as e:
        logging.debug(f"Failed to read Error cache: {e}")

    # ========== 缓存不存在时的处理 ==========
    if force_cache:
        # 强制缓存模式：返回空白图像
        blank_image = np.zeros((100, 100, 4), dtype=np.uint8)
        _, img_encoded = cv2.imencode('.png', blank_image)
        img_bytes = io.BytesIO(img_encoded.tobytes())
        return StreamingResponse(img_bytes, media_type="image/png")

    # ========== 动态生成（降级方案） ==========
    data_get = DataGet("image", surface_key, coil_id, "MASK", mask)
    npy_data = data_get.get_3d_data()

    # 检查数据是否有效
    if npy_data is None:
        logging.warning(f"3D data not found for coil_id={coil_id}, surface={surface_key}")
        # 返回空白图像
        blank_image = np.zeros((100, 100, 4), dtype=np.uint8)
        _, img_encoded = cv2.imencode('.png', blank_image)
        img_bytes = io.BytesIO(img_encoded.tobytes())
        return StreamingResponse(img_bytes, media_type="image/png")

    # mm 到原始单位的转换系数（与 ImageMosaic.py 中一致）
    scale_factor = 0.016229506582021713

    # 计算 median（中位数）
    valid_data = npy_data[npy_data > 1000]  # 只使用有效数据
    if len(valid_data) == 0:
        logging.warning(f"No valid 3D data for coil_id={coil_id}, surface={surface_key}")
        blank_image = np.zeros((100, 100, 4), dtype=np.uint8)
        _, img_encoded = cv2.imencode('.png', blank_image)
        img_bytes = io.BytesIO(img_encoded.tobytes())
        return StreamingResponse(img_bytes, media_type="image/png")
    median_z_int = int(np.median(valid_data))

    # 将 mm 阈值转换为原始单位
    threshold_down_units = int(threshold_down_mm / scale_factor)
    threshold_up_units = int(threshold_up_mm / scale_factor)

    # 计算实际阈值（原始单位）
    min_value = median_z_int - threshold_down_units
    max_value = median_z_int + threshold_up_units

    median_mm = median_z_int * scale_factor
    print(f"Error dynamic: median={median_mm:.1f}mm, range=[{median_mm - threshold_down_mm:.1f}, {median_mm + threshold_up_mm:.1f}]mm")

    # 数据处理
    rSize = (int(npy_data.shape[1] * scale), int(npy_data.shape[0] * scale))
    if scale < 0.99:
        npy_data = cv2.resize(npy_data, rSize, interpolation=cv2.INTER_AREA)

    height, width = npy_data.shape
    output_image = np.zeros((height, width, 4), dtype=np.uint8)  # BGRA 格式 透明

    # 蓝色区域：低于中位数 - threshold_down mm（塔形过小，远离侧）
    output_image[(npy_data > 1000) & (npy_data < min_value)] = [255, 0, 0, 255]  # B, G, R, A

    # 红色区域：高于中位数 + threshold_up mm（塔形过大，靠近侧）
    output_image[npy_data > max_value] = [0, 0, 255, 255]  # B, G, R, A

    _, img_encoded = cv2.imencode('.png', output_image)
    img_bytes = io.BytesIO(img_encoded.tobytes())
    e_t = time.time()
    print(f"Error generated dynamically: {e_t - sT:.3f}s (cache not found)")
    return StreamingResponse(img_bytes, media_type="image/png")

app.include_router(router)
