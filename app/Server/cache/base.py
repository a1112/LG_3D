import io
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np
from PIL import Image
from cachetools import TTLCache, cached

# 解除 PIL 对单张图片像素数量的安全限制，避免大幅面图像触发 DecompressionBombError。
Image.MAX_IMAGE_PIXELS = None

def _should_use_testdata() -> bool:
    """检查是否应该使用TestData的多种方式"""
    # 方式1: 检查CONFIG_3D目录下的developer_mode=true文件
    config_dir = Path(r"D:\CONFIG_3D")
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
        except:
            pass
    
    # 方式3: 检查环境变量
    import os
    if os.getenv("API_DEVELOPER_MODE", "").lower() in {"1", "true", "yes", "on"}:
        return True
    
    # 方式4: 尝试从CONFIG获取（如果已初始化）
    try:
        from CONFIG import developer_mode, isLoc
        return developer_mode and isLoc
    except:
        pass
    
    return False


_TESTDATA_COIL_ID = "125143"
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_TESTDATA_DIR = _PROJECT_ROOT / "TestData" / _TESTDATA_COIL_ID


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
    在开发者模式 + 本地环境下，将图片路径映射到 TestData/125143。
    其余情况直接返回原路径。
    """
    path_obj = Path(original_path)

    if not _should_use_testdata():
        return path_obj
    if not _TESTDATA_DIR.exists():
        return path_obj

    try:
        parts = path_obj.parts
        if "preview" in parts:
            type_name = path_obj.stem
            preview_dir = _TESTDATA_DIR / "preview"
            for ext in (path_obj.suffix, ".png", ".jpg", ".jpeg"):
                if not ext:
                    continue
                candidate = preview_dir / f"{type_name}{ext}"
                if candidate.exists():
                    return candidate
            return path_obj
        # 其他图像：.../<coil_id>/<folder>/<type>.<ext>
        folder_name = path_obj.parent.name
        type_name = path_obj.stem
        target_dir = _TESTDATA_DIR / folder_name

        for ext in (path_obj.suffix, ".png", ".jpg", ".jpeg"):
            if not ext:
                continue
            candidate = target_dir / f"{type_name}{ext}"
            if candidate.exists():
                return candidate
    except Exception as e:  # pragma: no cover - 映射失败时保留原路径
        print(e)
        return path_obj

    return path_obj


def _resolve_3d_path(original_path: str) -> Path:
    """
    在开发者模式 + 本地环境下，将任意 coil 的 3D 文件映射到固定 TestData/125143 的 3D 示例数据。

    注意：3D 数据不在 jpg/png 等子目录中，而是直接位于 TestData 根目录（例如 TestData/125143/3D.npz）。
    """
    path_obj = Path(original_path)
    if not _should_use_testdata():
        return path_obj
    if not _TESTDATA_DIR.exists():
        return path_obj

    for name in ("3D.npz", "3D.npy"):
        candidate = _TESTDATA_DIR / name
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

    def __init__(self, cache_size: int = 128, ttl: int = 200) -> None:
        self.cache_size = cache_size
        self.ttl = ttl
        self._cache_image_byte = self._build_image_byte_cache()
        self._mask_cache_image_byte = self._build_mask_image_cache()
        self._cache_image_pil = self._build_pil_cache()
        self._cache_image_clip = self._build_clip_cache()

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
                logging.info("get_image %s took %.2fs", path, elapsed)
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

    def _build_image_byte_cache(self):
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=self.ttl))
        def _load_image_byte(path: str) -> Optional[bytes]:
            start = time.perf_counter()
            data = self._load_image_bytes(path)
            elapsed = time.perf_counter() - start
            logging.info("cache miss image byte %s took %.2fs", path, elapsed)
            return data

        return _load_image_byte

    def _build_pil_cache(self):
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=self.ttl))
        def _load_image_pil(path: str) -> Optional[Image.Image]:
            image_byte = self._cache_image_byte(path)
            if image_byte is None:
                return None
            start = time.perf_counter()
            pil_img = Image.open(io.BytesIO(image_byte)).convert("L")
            elapsed = time.perf_counter() - start
            logging.info("cache miss image pil %s took %.2fs", path, elapsed)
            return pil_img

        return _load_image_pil

    def _build_clip_cache(self):
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=self.ttl))
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
            re_dict = defaultdict(dict)
            for row in range(count):
                for col in range(count):
                    tile = image[col * h_height:(col + 1) * h_height, row * w_width:(row + 1) * w_width]
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
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=self.ttl))
        def _load_mask_image_byte(path: str, mask_path: str) -> Optional[bytes]:
            start = time.perf_counter()
            base_image_bytes = self._cache_image_byte(path)
            if base_image_bytes is None:
                return None
            mask_image_bytes = self._cache_image_byte(mask_path)
            if mask_image_bytes is None:
                return None

            image = Image.open(io.BytesIO(base_image_bytes))
            mask_image = Image.open(io.BytesIO(mask_image_bytes))

            image = image.convert("RGBA")
            alpha = Image.new("L", image.size, 255)
            alpha.paste(mask_image, (0, 0))
            image.putalpha(alpha)

            png_byte_arr = io.BytesIO()
            image.save(png_byte_arr, format="PNG")
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
