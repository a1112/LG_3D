"""
缓存生成工具
用于在 AlgServer 和 Alg2DServer 存储原图时生成缓存
"""
import cv2
import numpy as np
from pathlib import Path
from PIL import Image
from typing import Optional


def generate_gray_thumbnail(
    npy_data: np.ndarray,
    cache_dir: Path,
    size: int = 1024,
    quality: int = 85
) -> bool:
    """
    生成 GRAY 灰度缩略图并缓存

    Args:
        npy_data: 3D 数据
        cache_dir: 缓存目录
        size: 缩略图尺寸
        quality: JPEG 质量

    Returns:
        是否成功生成
    """
    try:
        # 归一化到 0-255
        clip_npy = np.clip(npy_data, 0, 255)
        clip_npy = (clip_npy / 255 * 255).astype(np.uint8)

        # 缩放到缩略图尺寸
        h, w = clip_npy.shape[:2]
        scale = size / max(h, w)
        if scale < 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            clip_npy = cv2.resize(clip_npy, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # 转换为 BGR 格式（便于 JPEG 编码）
        gray_bgr = cv2.cvtColor(clip_npy, cv2.COLOR_GRAY2BGR)

        # 编码并保存
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "thumbnail_1024.jpg"

        ok, buf = cv2.imencode('.jpg', gray_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if ok:
            cache_path.write_bytes(buf.tobytes())
            return True

        return False

    except Exception as e:
        print(f"Failed to generate GRAY thumbnail: {e}")
        return False


def generate_jet_thumbnail(
    npy_data: np.ndarray,
    cache_dir: Path,
    mask: Optional[np.ndarray] = None,
    size: int = 1024,
    min_value: int = 0,
    max_value: int = 255,
    quality: int = 85
) -> bool:
    """
    生成 JET 伪彩色缩略图并缓存

    Args:
        npy_data: 3D 数据
        cache_dir: 缓存目录
        mask: 可选的掩码
        size: 缩略图尺寸
        min_value: 最小值
        max_value: 最大值
        quality: JPEG 质量

    Returns:
        是否成功生成
    """
    try:
        # 归一化到 0-255
        clip_npy = np.clip(npy_data, min_value, max_value)
        clip_npy = (clip_npy - min_value) / (max_value - min_value) * 255
        clip_npy = clip_npy.astype(np.uint8)

        # 缩放到缩略图尺寸
        h, w = clip_npy.shape[:2]
        scale = size / max(h, w)
        if scale < 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            clip_npy = cv2.resize(clip_npy, (new_w, new_h), interpolation=cv2.INTER_AREA)
            if mask is not None:
                mask = cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_NEAREST)

        # 应用 JET 颜色映射
        colored_image = cv2.applyColorMap(clip_npy, cv2.COLORMAP_JET)

        # 应用掩码
        if mask is not None:
            colored_image = cv2.bitwise_and(colored_image, colored_image, mask=mask)

        # 编码并保存
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "thumbnail_1024.jpg"

        ok, buf = cv2.imencode('.jpg', colored_image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if ok:
            cache_path.write_bytes(buf.tobytes())
            return True

        return False

    except Exception as e:
        print(f"Failed to generate JET thumbnail: {e}")
        return False


def get_gray_cache_dir(image_path: str) -> Path:
    """
    获取 GRAY 缓存目录

    Args:
        image_path: 原始图像路径

    Returns:
        缓存目录 Path
    """
    path_obj = Path(image_path)
    if path_obj.parent.name in {"jpg", "png"}:
        coil_dir = path_obj.parent.parent
    else:
        coil_dir = path_obj.parent

    return coil_dir / "cache" / "falsecolor" / "gray"
