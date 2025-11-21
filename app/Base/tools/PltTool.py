import cv2
import numpy as np
from PIL import Image

from CONFIG import SaveImageType, RendererList, serverConfigProperty
from Init import ColorMaps, PreviewSize


def getNoZeero(npy, savePath, mask):
    non_zero_elements = npy[npy != 0]
    median_non_zero = np.median(non_zero_elements)
    start = median_non_zero + serverConfigProperty.colorFromValue
    step = median_non_zero + serverConfigProperty.colorToValue

    for index in range(0, 1):
        npy__ = npy.copy()
        leftValue = index * step + start
        rightValue = (index + 1) * step + start
        npy__[npy__ < leftValue] = 0
        npy__[npy__ > rightValue] = 0
        non_zero_elements = npy__[npy__ != 0]
        a, b = start, start + step
        # 将图像裁剪到指定的范围 [a, b]
        depth_map_clipped = np.clip(npy__, a, b)
        # 将裁剪后的图像缩放到 [0, 255] 的范围
        depth_map_scaled = ((depth_map_clipped - a) / (b - a)) * 255
        # 转换为 uint8 类型
        depth_map_uint8 = depth_map_scaled.astype(np.uint8)
        # 定义所有颜色映射类型

        # 应用并保存每种颜色映射
        for name, colormap in ColorMaps.items():
            if name not in RendererList:
                continue
            depth_map_color = cv2.applyColorMap(depth_map_uint8, colormap)
            # depth_map_color = cv2.bitwise_and(depth_map_color, depth_map_color, mask=maskImage)
            save_ = str(savePath / (name + SaveImageType))
            image = Image.fromarray(depth_map_color)
            image.save(save_)

            image_rgba = image.convert("RGBA")
            image_rgba.putalpha(mask)
            save_png = savePath / "mask" / (name + SaveImageType)
            image_rgba.save(save_png)

            save_preview = str(savePath / "preview" / (name + SaveImageType))
            (savePath / "preview").mkdir(parents=True, exist_ok=True)
            image.thumbnail(PreviewSize)
            image.save(save_preview)
    return non_zero_elements
