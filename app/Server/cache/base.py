import io
import logging
import os
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np
from PIL import Image
from testdata_config import get_testdata_asset_dir, get_testdata_dir

from .bounded_cache import (MemoryBoundedTTLCache, memory_budget_bytes,
                            singleflight_cached)

# 解除 PIL 对单张图片像素数量的安全限制，避免大幅面图像触发 DecompressionBombError。
Image.MAX_IMAGE_PIXELS = None

def _should_use_testdata() -> bool:
    """检查是否应该使用TestData的多种方式"""
    config_dir = _config_dir()
    # 方式1: 检查CONFIG_3D目录下的developer_mode=true文件
    if (config_dir / "developer_mode=true").exists():
        return True
    
    # 方式2: 检查测试模式配置文件
    test_mode_config = config_dir / "test_mode_config.json"
    if test_mode_config.exists():
        try:
            import json
            with open(test_mode_config, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if config.get("test_mode", False):
                    return True
        except Exception as e:
            logging.debug("test mode config read failed: %s", e)
    
    # 方式3: 检查环境变量
    import os
    if os.getenv("API_DEVELOPER_MODE", "").lower() in {"1", "true", "yes", "on"}:
        return True
    
    # 方式4: 尝试从CONFIG获取（如果已初始化）
    try:
        from Base import CONFIG
        return CONFIG.developer_mode and CONFIG.isLoc
    except Exception as e:
        logging.debug("developer mode config check failed: %s", e)
    
    return False


def _config_dir() -> Path:
    try:
        from Base import CONFIG
        return Path(CONFIG.base_config_folder)
    except Exception as e:
        logging.debug("CONFIG base folder unavailable, use env fallback: %s", e)
        return Path(os.getenv("CONFIG_3D_DIR", r"D:\CONFIG_3D"))


_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class CacheComponent(ABC):
    """
    Base component interface so providers can run startup/shutdown hooks.
    """

    def startup(self) -> None:  # pragma: no cover - hook for external services
        return None

    def shutdown(self) -> None:  # pragma: no cover - hook for external services
        return None


def _resolve_image_path(original_path: str) -> Path:
    """
    在开发者模式 + 本地环境下，将图片路径映射到当前 TestData 目录。
    其余情况直接返回原路径。

    注意：现在所有文件都保存为 .jpg 格式，优先尝试 .jpg
    """
    path_obj = Path(original_path)

    if not _should_use_testdata():
        return path_obj
    testdata_dir = get_testdata_asset_dir(path_obj)
    if not testdata_dir.exists():
        return path_obj

    try:
        parts = path_obj.parts
        if "preview" in parts:
            type_name = path_obj.stem
            preview_dir = testdata_dir / "preview"
            # 优先尝试 .jpg（当前保存格式），然后才是其他格式
            for ext in (path_obj.suffix, ".jpg", ".jpeg", ".png"):
                if not ext:
                    continue
                candidate = preview_dir / f"{type_name}{ext}"
                if candidate.exists():
                    return candidate
            return path_obj
        # 其他图像：.../<coil_id>/<folder>/<type>.<ext>
        folder_name = path_obj.parent.name
        type_name = path_obj.stem
        target_dir = testdata_dir / folder_name

        # 优先尝试 .jpg（当前保存格式）
        for ext in (path_obj.suffix, ".jpg", ".jpeg", ".png"):
            if not ext:
                continue
            candidate = target_dir / f"{type_name}{ext}"
            if candidate.exists():
                return candidate
    except Exception as e:  # pragma: no cover - 映射失败时保留原路径
        logging.debug("developer_mode image path mapping failed: %s", e)
        return path_obj

    return path_obj


def _resolve_3d_path(original_path: str) -> Path:
    """
    在开发者模式 + 本地环境下，将任意 coil 的 3D 文件映射到当前 TestData 示例数据。

    注意：3D 数据不在 jpg/png 等子目录中，而是直接位于 TestData 根目录（例如 TestData/to/193113/3D.npz）。
    """
    path_obj = Path(original_path)
    if not _should_use_testdata():
        return path_obj
    testdata_dir = get_testdata_asset_dir(path_obj)
    if not testdata_dir.exists():
        return path_obj

    for name in ("3D.npz", "3D.npy"):
        candidate = testdata_dir / name
        if candidate.exists():
            if candidate != path_obj:
                logging.info("developer_mode: map 3D %s -> %s", path_obj, candidate)
            return candidate
    return path_obj


class BaseImageCache(CacheComponent):
    """
    Shared image cache behavior (PIL conversion, clipping, mask merging).
    Subclasses only implement `_load_image_bytes`.
    """

    _CACHE_BUDGET_PERCENT = {
        "bytes": 30,
        "pil": 40,
        "clip": 20,
        "mask": 10,
    }

    def __init__(self,
                 cache_size: int = 128,
                 ttl: int = 600,
                 max_memory_mb: Optional[int] = None) -> None:
        self.cache_size = cache_size
        self.ttl = ttl
        if max_memory_mb is None:
            self.max_memory_bytes = memory_budget_bytes(
                "CACHE_IMAGE_INSTANCE_MAX_MB", 128)
        else:
            self.max_memory_bytes = max(int(max_memory_mb), 1) * 1024 * 1024
        self._cache_image_byte = self._build_image_byte_cache()
        self._mask_cache_image_byte = self._build_mask_image_cache()
        self._cache_image_pil = self._build_pil_cache()
        self._cache_image_clip = self._build_clip_cache()

    def _new_cache(self, kind: str) -> MemoryBoundedTTLCache:
        percent = self._CACHE_BUDGET_PERCENT[kind]
        max_bytes = max(self.max_memory_bytes * percent // 100, 1)
        return MemoryBoundedTTLCache(max_bytes=max_bytes,
                                     max_entries=self.cache_size,
                                     ttl=self.ttl)

    @abstractmethod
    def _load_image_bytes(self, path: str) -> Optional[bytes]:
        """
        Load raw image bytes from the underlying storage.
        """

    def get_image(self, path: str, pil: bool = False, clip_num: int = 0) -> Optional[Any]:
        start = time.perf_counter()
        try:
            if pil:
                result = self._cache_image_pil(path)
            elif clip_num:
                result = self._cache_image_clip(path, clip_num)
            else:
                result = self._cache_image_byte(path)

            elapsed = time.perf_counter() - start
            if elapsed >= 0.01:
                logging.info("[CACHE] get_image %s took %.3fs", path, elapsed)
            return result
        except Exception as exc:  # pragma: no cover - defensive, keep same behavior as before
            logging.exception("Error loading image: %s", exc)
            return None

    def get_mask_image(self, path: str, mask_path: str) -> Optional[bytes]:
        try:
            return self._mask_cache_image_byte(path, mask_path)
        except Exception as exc:  # pragma: no cover
            logging.exception("Error loading mask image: %s", exc)
            return None

    def clear_cache(self) -> None:
        self._cache_image_byte.cache_clear()
        self._mask_cache_image_byte.cache_clear()
        self._cache_image_pil.cache_clear()
        self._cache_image_clip.cache_clear()

    def shutdown(self) -> None:
        self.clear_cache()

    def cache_stats(self) -> dict:
        layers = {
            "bytes": self._cache_image_byte.cache,
            "pil": self._cache_image_pil.cache,
            "clip": self._cache_image_clip.cache,
            "mask": self._mask_cache_image_byte.cache,
        }
        detail = {
            name: {
                "entries": len(cache),
                "bytes": cache.currsize,
                "maxBytes": cache.maxsize,
                "maxEntries": cache.max_entries,
            }
            for name, cache in layers.items()
        }
        return {
            "entries": sum(item["entries"] for item in detail.values()),
            "bytes": sum(item["bytes"] for item in detail.values()),
            "maxBytes": sum(item["maxBytes"] for item in detail.values()),
            "layers": detail,
        }

    def _build_image_byte_cache(self):
        @singleflight_cached(self._new_cache("bytes"))
        def _load_image_byte(path: str) -> Optional[bytes]:
            start = time.perf_counter()
            data = self._load_image_bytes(path)
            elapsed = time.perf_counter() - start
            logging.info("cache miss image byte %s took %.2fs", path, elapsed)
            return data

        def _load_image_byte_wrapper(path: str) -> Optional[bytes]:
            # 规范化路径以确保缓存一致性（解决路径大小写/分隔符问题）
            normalized_path = str(Path(path).resolve())
            return _load_image_byte(normalized_path)

        # Keep the cachetools management API on the normalizing wrapper.  The
        # previous wrapper dropped ``cache_clear``, making provider shutdown
        # and the AREA cache-clear endpoint fail with AttributeError.
        _load_image_byte_wrapper.cache = _load_image_byte.cache
        _load_image_byte_wrapper.cache_clear = _load_image_byte.cache_clear
        _load_image_byte_wrapper.cache_info = _load_image_byte.cache_info
        _load_image_byte_wrapper.cache_lock = _load_image_byte.cache_lock

        return _load_image_byte_wrapper

    def _build_pil_cache(self):
        @singleflight_cached(self._new_cache("pil"))
        def _load_image_pil(path: str) -> Optional[Image.Image]:
            image_byte = self._cache_image_byte(path)
            if image_byte is None:
                return None
            start = time.perf_counter()
            with Image.open(io.BytesIO(image_byte)) as source_image:
                pil_img = source_image.convert("L")
            elapsed = time.perf_counter() - start
            logging.info("cache miss image pil %s took %.2fs", path, elapsed)
            return pil_img

        return _load_image_pil

    def _build_clip_cache(self):
        @singleflight_cached(self._new_cache("clip"))
        def _load_image_clip(path: str, count: int) -> Optional[dict]:
            start = time.perf_counter()
            image_bytes = self._cache_image_byte(path)
            if image_bytes is None:
                return None
            np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
            image = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)
            if image is None:
                logging.error("cv2 imdecode failed for %s", path)
                return None
            h, w = image.shape[:2]
            w_width = w // count
            h_height = h // count
            if w_width <= 0 or h_height <= 0:
                return None
            re_dict = defaultdict(dict)
            for row in range(count):
                for col in range(count):
                    x1 = col * w_width
                    y1 = row * h_height
                    x2 = w if col == count - 1 else x1 + w_width
                    y2 = h if row == count - 1 else y1 + h_height
                    tile = image[y1:y2, x1:x2]
                    ok, buf = cv2.imencode(".jpg", tile)
                    if not ok:
                        logging.error("cv2 imencode failed for %s row=%s col=%s", path, row, col)
                        return None
                    re_dict[col][row] = buf.tobytes()
            elapsed = time.perf_counter() - start
            logging.info("cache miss image clip %s count=%s took %.2fs", path, count, elapsed)
            return re_dict

        return _load_image_clip

    def _build_mask_image_cache(self):
        @singleflight_cached(self._new_cache("mask"))
        def _load_mask_image_byte(path: str, mask_path: str) -> Optional[bytes]:
            start = time.perf_counter()
            base_image_bytes = self._cache_image_byte(path)
            if base_image_bytes is None:
                return None
            mask_image_bytes = self._cache_image_byte(mask_path)
            if mask_image_bytes is None:
                return None

            with Image.open(io.BytesIO(base_image_bytes)) as source_image:
                with Image.open(io.BytesIO(mask_image_bytes)) as mask_image:
                    image = source_image.convert("RGBA")
                    alpha = Image.new("L", image.size, 255)
                    try:
                        alpha.paste(mask_image, (0, 0))
                        image.putalpha(alpha)

                        png_byte_arr = io.BytesIO()
                        image.save(png_byte_arr, format="PNG")
                    finally:
                        alpha.close()
                        image.close()
            png_byte_arr.seek(0)
            elapsed = time.perf_counter() - start
            logging.info("cache miss mask image %s + %s took %.2fs", path, mask_path, elapsed)
            return png_byte_arr.getvalue()

        return _load_mask_image_byte


class Base3dCache(CacheComponent):
    """
    Base class for 3D data caching.
    """

    def clear_cache(self) -> None:
        raise NotImplementedError

    def get_data(self, path: str):
        raise NotImplementedError
