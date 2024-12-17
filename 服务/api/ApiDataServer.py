import io
import time

import cv2
import numpy as np

from property.Types import Point2D
from property.Data3D import LineData
from tools.DataGet import DataGet
from fastapi.responses import StreamingResponse
from PIL import Image
from ._tool_ import get_bool

from fastapi import APIRouter
from .api_core import app

router = APIRouter(tags=["深度数据访问服务"])

@router.get("/coilData/heightData/{surface_key:str}/{coil_id:str}")
async def get_height_data(surface_key, coil_id: str, x1: int = 0, y1: int = 0, x2: int = 0, y2: int = 0):
    data_get = DataGet("image", surface_key, coil_id, "MASK", False)
    mask_image = data_get.get_image(pil=True)
    npy_data = data_get.get_3d_data()

    mask_image = np.array(mask_image)
    if not y2 and not x2:
        x2, y2 = x1 + 10, y1
    line_data = LineData(npy_data, mask_image, Point2D(x1, y1), Point2D(x2, y2))
    return line_data.all_image_line_points().tolist()

@router.get("/coilData/heightPoint/{surface_key:str}/{coil_id:str}")
async def get_height_point(surface_key, coil_id: str, x: int = 0, y: int = 0):
    data_get = DataGet("image", surface_key, coil_id, "MASK", False)
    npy_data = data_get.get_3d_data()
    try:
        return int(npy_data[int(y)][int(x)])
    except (BaseException,) as e:
        print(e)
        return "error"


@router.get("/coilData/Render/{surfaceKey:str}/{coil_id:str}")
async def getRender(surfaceKey, coil_id: str, scale=1, mask: bool = True, minValue=0, maxValue=255):
    mask = get_bool(mask)
    scale = float(scale)
    sT = time.time()
    minValue = int(minValue)
    maxValue = int(maxValue)
    dataGet = DataGet("image", surfaceKey, coil_id, "MASK", False)
    npy_data = dataGet.get_3d_data()
    mask_image = dataGet.get_image()
    mask_image = Image.open(io.BytesIO(mask_image))
    mask_image = np.array(mask_image)
    rSize = (int(npy_data.shape[1] * scale), int(npy_data.shape[0] * scale))
    clip_npy = np.clip(npy_data, minValue, maxValue)
    clip_npy = (clip_npy - minValue) / (maxValue - minValue) * 255
    clip_npy = clip_npy.astype(np.uint8)
    if scale < 0.99:
        print(rSize)
        clip_npy = cv2.resize(clip_npy, rSize)
        mask_image = cv2.resize(mask_image, rSize)

    colored_image = cv2.applyColorMap(clip_npy, cv2.COLORMAP_JET)
    if mask:
        colored_image = cv2.bitwise_and(colored_image, colored_image, mask=mask_image)
    _, img_encoded = cv2.imencode('.png', colored_image)
    # 将编码后的图像转换为字节流
    img_bytes = io.BytesIO(img_encoded.tobytes())
    # 返回图像作为响应
    eT = time.time()
    print(eT - sT)
    return StreamingResponse(img_bytes, media_type="image/png")


@router.get("/coilData/Area/{surface_key:str}/{coil_id:str}")
async def get_area(surface_key, coil_id: str, scale=1, mask: bool = True, valueFrom=0, valueTo=255, r=255, g=0, b=0):
    mask = get_bool(mask)
    scale = float(scale)
    minValue, maxValue = int(valueFrom), int(valueTo)
    sT = time.time()
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
    output_image[(npy_data > minValue) & (npy_data < maxValue)] = color  # B, G, R, A
    _, img_encoded = cv2.imencode('.png', output_image)
    img_bytes = io.BytesIO(img_encoded.tobytes())
    eT = time.time()
    print(f"Processing Time: {eT - sT:.2f} seconds")
    return StreamingResponse(img_bytes, media_type="image/png")


@router.get("/coilData/Error/{surface_key:str}/{coil_id:str}")
async def get_error(
        surface_key: str,
        coil_id: str,
        scale: float = 1.0,
        mask: bool = True,
        min_value: int = 0,
        max_value: int = 255
):
    mask = get_bool(mask)
    scale = float(scale)
    min_value, max_value = int(min_value), int(max_value)
    sT = time.time()
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

    # 蓝色区域
    output_image[(npy_data > 1000) & (npy_data < min_value)] = [255, 0, 0, 255]  # B, G, R, A

    # 红色区域
    output_image[npy_data > max_value] = [0, 0, 255, 255]  # B, G, R, A
    # 缩放处理
    # 应用伪彩色和透明通道
    _, img_encoded = cv2.imencode('.png', output_image)
    img_bytes = io.BytesIO(img_encoded.tobytes())
    e_t = time.time()
    print(f"Processing Time: {e_t - sT:.2f} seconds")
    return StreamingResponse(img_bytes, media_type="image/png")

app.include_router(router)