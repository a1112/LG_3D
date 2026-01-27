import logging
import threading
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from cachetools import TTLCache

from Base.CONFIG import serverConfigProperty
from .base import _resolve_image_path
from .memory_cache import MemoryImageCache


class FalseColorCache(MemoryImageCache):
    """伪彩色图像缓存 (GRAY/JET) - 缓存缩略图加速加载"""

    def __init__(self, cache_size: int = 64, ttl: int = 600,
                 thumbnail_size: int = 1024) -> None:
        super().__init__(cache_size=cache_size, ttl=ttl)
        self.thumbnail_size = thumbnail_size
        self._lock = threading.Lock()

    def _cache_dir(self, path: str, colormap: str = "JET") -> Path:
        """获取缓存目录"""
        path_obj = _resolve_image_path(path)
        if path_obj.parent.name in {"jpg", "png"}:
            coil_dir = path_obj.parent.parent
        else:
            coil_dir = path_obj.parent

        # 统一使用小写的目录名
        colormap_name = colormap.lower()
        return coil_dir / "cache" / "falsecolor" / colormap_name

    def _cache_path(self, cache_dir: Path) -> Path:
        """获取缓存文件路径"""
        return cache_dir / f"thumbnail_{self.thumbnail_size}.jpg"

    def get_thumbnail(self, path: str, colormap: str = "JET") -> Optional[bytes]:
        """
        获取缓存的缩略图

        Args:
            path: 原始3D数据文件路径
            colormap: 颜色映射 ("JET" 或其他 OpenCV COLORMAP)

        Returns:
            缓存的缩略图字节数据，如果不存在则返回 None
        """
        cache_dir = self._cache_dir(path, colormap)
        cache_path = self._cache_path(cache_dir)

        if cache_path.exists():
            return cache_path.read_bytes()
        return None

    def generate_thumbnail(self, npy_data: np.ndarray,
                          mask: Optional[np.ndarray] = None,
                          colormap: int = cv2.COLORMAP_JET,
                          min_value: int = 0,
                          max_value: int = 255) -> Optional[bytes]:
        """
        生成缩略图

        Args:
            npy_data: 3D 数据
            mask: 可选的掩码
            colormap: OpenCV 颜色映射 (cv2.COLORMAP_JET 或 -1 表示灰度)
            min_value: 最小值
            max_value: 最大值

        Returns:
            JPEG 编码的缩略图字节数据，失败返回 None
        """
        try:
            # 归一化到 0-255
            clip_npy = np.clip(npy_data, min_value, max_value)
            clip_npy = (clip_npy - min_value) / (max_value - min_value) * 255
            clip_npy = clip_npy.astype(np.uint8)

            # 缩放到缩略图尺寸
            h, w = clip_npy.shape[:2]
            scale = self.thumbnail_size / max(h, w)
            if scale < 1.0:
                new_w = int(w * scale)
                new_h = int(h * scale)
                clip_npy = cv2.resize(clip_npy, (new_w, new_h), interpolation=cv2.INTER_AREA)
                if mask is not None:
                    mask = cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_NEAREST)

            # 应用颜色映射或保持灰度
            if colormap == -1:
                # GRAY 模式：保持灰度，转换为 BGR
                colored_image = cv2.cvtColor(clip_npy, cv2.COLOR_GRAY2BGR)
            else:
                # 应用颜色映射
                colored_image = cv2.applyColorMap(clip_npy, colormap)

            # 应用掩码
            if mask is not None:
                if colormap == -1:
                    # GRAY 模式掩码需要 3 通道
                    mask_3ch = cv2.merge([mask, mask, mask])
                    colored_image = cv2.bitwise_and(colored_image, colored_image, mask=mask_3ch)
                else:
                    colored_image = cv2.bitwise_and(colored_image, colored_image, mask=mask)

            # 编码为 JPEG
            ok, buf = cv2.imencode('.jpg', colored_image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ok:
                return buf.tobytes()
            return None

        except Exception as e:
            logging.error(f"Failed to generate thumbnail: {e}")
            return None

    def get_or_generate(self, path: str, npy_data: np.ndarray,
                       mask: Optional[np.ndarray] = None,
                       colormap: int = cv2.COLORMAP_JET,
                       min_value: int = 0,
                       max_value: int = 255) -> Tuple[Optional[bytes], bool]:
        """
        获取或生成缩略图（GRAY 和 JET 都使用缓存）

        Args:
            path: 原始3D数据文件路径
            npy_data: 3D 数据
            mask: 可选的掩码
            colormap: OpenCV 颜色映射
                - cv2.COLORMAP_JET: JET 模式，使用缓存
                - -1: GRAY 模式，使用缓存

        Returns:
            (缩略图字节数据, 是否来自缓存)
        """
        # 确定颜色映射名称
        colormap_name = "GRAY" if colormap == -1 else "JET"
        
        # 尝试从缓存读取
        cached = self.get_thumbnail(path, colormap_name)
        if cached:
            return cached, True

        # 生成新的缩略图
        with self._lock:
            # 双检查，避免重复生成
            cached = self.get_thumbnail(path, colormap_name)
            if cached:
                return cached, True

            # 生成并缓存
            thumbnail = self.generate_thumbnail(npy_data, mask, colormap, min_value, max_value)
            if thumbnail:
                cache_dir = self._cache_dir(path, colormap_name)
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_path = self._cache_path(cache_dir)
                cache_path.write_bytes(thumbnail)
                logging.debug(f"Cached {colormap_name} thumbnail: {cache_path}")
                return thumbnail, False

        return None, False
