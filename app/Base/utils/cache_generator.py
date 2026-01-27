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
    npy_data: Optional[np.ndarray] = None,
    cache_dir: Optional[Path] = None,
    source_image: Optional[Path] = None,
    size: int = 1024,
    quality: int = 85
) -> bool:
    """
    生成 GRAY 灰度缩略图并缓存

    Args:
        npy_data: 3D 数据（已弃用，保留兼容性）
        cache_dir: 缓存目录
        source_image: 源图像文件路径（优先使用）
        size: 缩略图尺寸
        quality: JPEG 质量

    Returns:
        是否成功生成
    """
    try:
        # 优先从源图像文件生成
        if source_image and source_image.exists():
            img = Image.open(source_image)
            # 确保是 RGB 模式
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 缩放到缩略图尺寸
            img.thumbnail((size, size), Image.Resampling.LANCZOS)

            # 编码并保存
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = cache_dir / "thumbnail_1024.jpg"

            img.save(cache_path, quality=quality, optimize=True)
            return True

        # 兼容旧代码：从 numpy 数据生成
        if npy_data is not None and cache_dir is not None:
            clip_npy = np.clip(npy_data, 0, 255)
            clip_npy = clip_npy.astype(np.uint8)

            h, w = clip_npy.shape[:2]
            scale = size / max(h, w)
            if scale < 1.0:
                new_w = int(w * scale)
                new_h = int(h * scale)
                clip_npy = cv2.resize(clip_npy, (new_w, new_h), interpolation=cv2.INTER_AREA)

            gray_bgr = cv2.cvtColor(clip_npy, cv2.COLOR_GRAY2BGR)

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
    npy_data: Optional[np.ndarray] = None,
    cache_dir: Optional[Path] = None,
    source_image: Optional[Path] = None,
    mask: Optional[np.ndarray] = None,
    size: int = 1024,
    min_value: int = 0,
    max_value: int = 255,
    quality: int = 85
) -> bool:
    """
    生成 JET 伪彩色缩略图并缓存

    Args:
        npy_data: 3D 数据（已弃用，保留兼容性）
        cache_dir: 缓存目录
        source_image: 源图像文件路径（优先使用）
        mask: 可选的掩码
        size: 缩略图尺寸
        min_value: 最小值
        max_value: 最大值
        quality: JPEG 质量

    Returns:
        是否成功生成
    """
    try:
        # 优先从源图像文件生成
        if source_image and source_image.exists():
            img = Image.open(source_image)
            # 确保是 RGB 模式
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 缩放到缩略图尺寸
            img.thumbnail((size, size), Image.Resampling.LANCZOS)

            # 编码并保存
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = cache_dir / "thumbnail_1024.jpg"

            img.save(cache_path, quality=quality, optimize=True)
            return True

        # 兼容旧代码：从 numpy 数据生成
        if npy_data is not None and cache_dir is not None:
            clip_npy = np.clip(npy_data, min_value, max_value)
            clip_npy = (clip_npy - min_value) / (max_value - min_value) * 255
            clip_npy = clip_npy.astype(np.uint8)

            h, w = clip_npy.shape[:2]
            scale = size / max(h, w)
            if scale < 1.0:
                new_w = int(w * scale)
                new_h = int(h * scale)
                clip_npy = cv2.resize(clip_npy, (new_w, new_h), interpolation=cv2.INTER_AREA)
                if mask is not None:
                    mask = cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_NEAREST)

            colored_image = cv2.applyColorMap(clip_npy, cv2.COLORMAP_JET)

            if mask is not None:
                colored_image = cv2.bitwise_and(colored_image, colored_image, mask=mask)

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


def get_error_cache_dir(image_path: str) -> Path:
    """
    获取 Error 缓存目录（存储 Error.png）

    Args:
        image_path: 原始图像路径

    Returns:
        png 目录 Path
    """
    path_obj = Path(image_path)
    # Error.png 直接保存在 png 目录下，与其他图像并列
    if path_obj.parent.name in {"jpg", "png"}:
        coil_dir = path_obj.parent.parent
    else:
        coil_dir = path_obj.parent

    return coil_dir / "png"


def generate_error_image(
    npy_data: np.ndarray,
    png_dir: Path,
    median_z_int: int = 0,
    threshold_down: int = 100,
    threshold_up: int = 100,
    scale_factor: float = 0.016229506582021713
) -> bool:
    """
    生成 Error 塔形报警图像并保存到 png 目录

    图像格式：
    - 蓝色区域：低于基础平面 - threshold_down mm（塔形过小）
    - 红色区域：高于基础平面 + threshold_up mm（塔形过大）

    Args:
        npy_data: 3D 数据（原始单位）
        png_dir: png 目录路径
        median_z_int: 中位数值（原始单位，偏移量）
        threshold_down: 下限阈值（mm）
        threshold_up: 上限阈值（mm）
        scale_factor: mm 到原始单位的转换系数（每个原始单位对应的 mm 值）

    Returns:
        是否成功生成
    """
    try:
        import time
        s_t = time.time()

        height, width = npy_data.shape[:2]

        # 将 mm 阈值转换为原始单位
        threshold_down_units = int(threshold_down / scale_factor)
        threshold_up_units = int(threshold_up / scale_factor)

        # 计算实际阈值（原始单位）
        min_value = median_z_int - threshold_down_units
        max_value = median_z_int + threshold_up_units

        # 创建 BGRA 格式输出图像
        output_image = np.zeros((height, width, 4), dtype=np.uint8)

        # 蓝色区域：低于下限 (塔形过小，远离这一侧)
        # 1000 是一个基准值，低于这个值说明有效数据不足
        output_image[(npy_data > 1000) & (npy_data < min_value)] = [255, 0, 0, 255]  # B, G, R, A = 蓝色

        # 红色区域：高于上限 (塔形过大，靠近这一侧)
        output_image[npy_data > max_value] = [0, 0, 255, 255]  # B, G, R, A = 红色

        # 保存为 PNG 文件
        png_dir.mkdir(parents=True, exist_ok=True)
        error_path = png_dir / "Error.png"

        ok, buf = cv2.imencode('.png', output_image)
        if ok:
            error_path.write_bytes(buf.tobytes())
            e_t = time.time()
            median_mm = median_z_int * scale_factor
            min_mm = median_mm - threshold_down
            max_mm = median_mm + threshold_up
            print(f"Generated Error.png: {e_t - s_t:.3f}s, median={median_mm:.1f}mm, range=[{min_mm:.1f}, {max_mm:.1f}]mm")
            return True

        return False

    except Exception as e:
        print(f"Failed to generate Error image: {e}")
        return False
