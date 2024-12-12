import io
import time

import cv2
import numpy as np

from property.Types import Point2D
from property.Data3D import LineData
from tools.DataGet import DataGet
from fastapi.responses import StreamingResponse
from PIL import Image
from ApiBase import *


def getBool(value, defaultValue=True):
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        return bool(int(value))
    except ValueError:
        return defaultValue


@app.get("/coilData/heightData/{surfaceKey:str}/{coil_id:str}")
async def getHeightData(surfaceKey, coil_id: str, x1: int = 0, y1: int = 0, x2: int = 0, y2: int = 0):
    dataGet = DataGet("image", surfaceKey, coil_id, "MASK", False)
    jpgBytes = dataGet.get_image()
    mask_image = Image.open(io.BytesIO(jpgBytes))
    npy_data = dataGet.get_3d_data()

    mask_image = np.array(mask_image)
    if not y2 and not x2:
        x2, y2 = x1 + 10, y1
    lineData = LineData(npy_data, mask_image, Point2D(x1, y1), Point2D(x2, y2))
    # lenData = getLengthData(npy_data, mask_image, (x1, y1), (x2, y2))
    return lineData.all_image_line_points().tolist()
    # return lineData


@app.get("/coilData/heightPoint/{surfaceKey:str}/{coil_id:str}")
async def getHeightPoint(surfaceKey, coil_id: str, x: int = 0, y: int = 0):
    dataGet = DataGet("image", surfaceKey, coil_id, "MASK", False)
    npy_data = dataGet.get_3d_data()
    try:
        return int(npy_data[int(y)][int(x)])
    except BaseException:
        return "error"


@app.get("/coilData/Render/{surfaceKey:str}/{coil_id:str}")
async def getRender(surfaceKey, coil_id: str, scale=1, mask: bool = True, minValue=0, maxValue=255):
    mask = getBool(mask)
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


@app.get("/coilData/Area/{surfaceKey:str}/{coil_id:str}")
async def getArea(surfaceKey, coil_id: str, scale=1, mask: bool = True, valueFrom=0, valueTo=255, r=255, g=0, b=0):
    mask = getBool(mask)
    scale = float(scale)
    minValue, maxValue = int(valueFrom), int(valueTo)
    sT = time.time()
    # 数据获取
    data_get = DataGet("image", surfaceKey, coil_id, "MASK", mask)
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


# @app.get("/coilData/Error/{surfaceKey:str}/{coil_id:str}")
# async def getError(surfaceKey, coil_id: str, scale=1, mask: bool = True, minValue=0, maxValue=255):
#     mask = getBool(mask)
#     scale = float(scale)
#     sT = time.time()
#     minValue = int(minValue)
#     maxValue = int(maxValue)
#     dataGet = DataGet("image", surfaceKey, coil_id, "MASK", mask)
#     npy_data = dataGet.get_3d_data()
#     npy_data = npy_data.copy()
#     npy_data[(npy_data > minValue) & (npy_data < maxValue)] = 0  # 中间值设置 8
#     mask_image = dataGet.get_image()
#     mask_image = Image.open(io.BytesIO(mask_image))
#     mask_image = np.array(mask_image)
#     mask_image[npy_data < 10000] = 0
#     rSize = (int(npy_data.shape[1] * scale), int(npy_data.shape[0] * scale))
#     clip_npy = np.clip(npy_data, minValue, maxValue)
#     clip_npy = (clip_npy - minValue) / (maxValue - minValue) * 255
#     clip_npy = clip_npy.astype(np.uint8)
#     if scale < 0.99:
#         clip_npy = cv2.resize(clip_npy, rSize)
#         mask_image = cv2.resize(mask_image, rSize)
#     colored_image = cv2.applyColorMap(clip_npy, cv2.COLORMAP_JET)
#     colored_image = cv2.cvtColor(colored_image, cv2.COLOR_BGR2BGRA)
#     alpha_channel = np.zeros(colored_image.shape[:2], dtype=np.uint8)
#
#     # 将 mask_image 之外的区域设置为透明（0）
#     alpha_channel[mask_image > 0] = 255
#
#     # 将 Alpha 通道应用到图像上
#     colored_image[:, :, 3] = alpha_channel
#     _, img_encoded = cv2.imencode('.png', colored_image)
#     img_bytes = io.BytesIO(img_encoded.tobytes())
#     eT = time.time()
#     print(eT - sT)
#     return StreamingResponse(img_bytes, media_type="image/png")


@app.get("/coilData/Error/{surfaceKey:str}/{coil_id:str}")
async def get_error(
        surfaceKey: str,
        coil_id: str,
        scale: float = 1.0,
        mask: bool = True,
        minValue: int = 0,
        maxValue: int = 255
):
    mask = getBool(mask)
    scale = float(scale)
    minValue, maxValue = int(minValue), int(maxValue)
    sT = time.time()
    # 数据获取
    data_get = DataGet("image", surfaceKey, coil_id, "MASK", mask)
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
    output_image[(npy_data > 1000) & (npy_data < minValue)] = [255, 0, 0, 255]  # B, G, R, A

    # 红色区域
    output_image[npy_data > maxValue] = [0, 0, 255, 255]  # B, G, R, A
    # 缩放处理
    # 应用伪彩色和透明通道
    _, img_encoded = cv2.imencode('.png', output_image)
    img_bytes = io.BytesIO(img_encoded.tobytes())
    eT = time.time()
    print(f"Processing Time: {eT - sT:.2f} seconds")
    return StreamingResponse(img_bytes, media_type="image/png")
