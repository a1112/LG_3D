import io
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Optional

from PIL import Image
from cachetools import TTLCache, cached


class CacheComponent(ABC):
    """
    Base component interface so providers can run startup/shutdown hooks.
    """

    def startup(self) -> None:  # pragma: no cover - hook for external services
        return None

    def shutdown(self) -> None:  # pragma: no cover - hook for external services
        return None


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
        try:
            if pil:
                return self._cache_image_pil(path)
            if clip_num:
                return self._cache_image_clip(path, clip_num)
            return self._cache_image_byte(path)
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
            logging.info("load image byte %s", path)
            return self._load_image_bytes(path)

        return _load_image_byte

    def _build_pil_cache(self):
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=self.ttl))
        def _load_image_pil(path: str) -> Optional[Image.Image]:
            logging.info("load image pil %s", path)
            image_byte = self._cache_image_byte(path)
            if image_byte is None:
                return None
            return Image.open(io.BytesIO(image_byte)).convert("L")

        return _load_image_pil

    def _build_clip_cache(self):
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=self.ttl))
        def _load_image_clip(path: str, count: int) -> Optional[dict]:
            logging.info("load image clip %s %s", path, count)
            image = self.get_image(path, pil=True)
            if image is None:
                return None
            image = image  # type: Image.Image
            w, h = image.size
            w_width = w // count
            h_height = h // count
            re_dict = defaultdict(dict)
            for row in range(count):
                for col in range(count):
                    crop_image = image.crop((row * w_width, col * h_height, (row + 1) * w_width, (col + 1) * h_height))
                    img_byte_arr = io.BytesIO()
                    crop_image.save(img_byte_arr, format="jpeg")
                    img_byte_arr.seek(0)
                    re_dict[col][row] = img_byte_arr.getvalue()
            return re_dict

        return _load_image_clip

    def _build_mask_image_cache(self):
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=self.ttl))
        def _load_mask_image_byte(path: str, mask_path: str) -> Optional[bytes]:
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
