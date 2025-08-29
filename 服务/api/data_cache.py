
import io
import logging
import os
from collections import defaultdict
from datetime import time
from functools import lru_cache
from pathlib import Path
import time

import numpy as np
from PIL import Image
from cachetools import cached, LRUCache,TTLCache

class ImageCache:
    def __init__(self, cache_size=128):
        self.cache_size = cache_size
        self._cache_image_byte = self._cache_image_byte()
        self.mask_cache_image_byte = self._mask_cache_image_byte()
        self._cache_image_pil = self._cache_image_pil()
        self._cache_image_clip = self._cache_image_clip()

        self._cache = self._create_cache()

    def _cache_image_pil(self):
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=200))
        # @lru_cache(maxsize=self.cache_size)
        def _load_image_npy(path):
            logging.info(fr"load image npy {path}")

            image_byte = self.get_image(path)
            if image_byte is None:
                return None
            return Image.open(io.BytesIO(image_byte)).convert("L")

        return _load_image_npy

    def _cache_image_clip(self):
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=200))
        def _load_image_clip(path,count):
            logging.info(fr"load image clip {path} {count}")
            sT=time.time()
            image = self.get_image(path,pil=True)
            image:Image.Image
            if image is None:
                return None
            w, h = image.size
            w_width = w // count
            h_height = h // count
            re_dict=defaultdict(dict)
            for row in range(count):
                for col in range(count):
                    crop_image = image.crop(( row * w_width, col * h_height,(row + 1) * w_width,(col + 1) * h_height))
                    img_byte_arr = io.BytesIO()
                    crop_image.save(img_byte_arr, format='jpeg')
                    img_byte_arr.seek(0)
                    re_dict[col][row] = img_byte_arr.getvalue()
            logging.info(fr"load image clip time {time.time()-sT}")

            return re_dict

        return _load_image_clip

    def _cache_image_byte(self):
        # @lru_cache(maxsize=self.cache_size)
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=200))
        def _load_image_byte(path):
            logging.info(fr"load image byte {path}")
            if not Path(path).exists():
                logging.error(f" {path} does not exist")

                return None
            with open(path, 'rb') as f:
                logging.debug(f"loading image {path}")
                return f.read()

        return _load_image_byte

    def _mask_cache_image_byte(self):
        # @lru_cache(maxsize=self.cache_size)
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=200))
        def _load_image_byte(path, mask_path):
            binary_data = self._cache_image_byte(path)
            image = Image.open(io.BytesIO(binary_data))

            binary_data = self._cache_image_byte(mask_path)
            mask_image = Image.open(io.BytesIO(binary_data))

            image = image.convert("RGBA")
            mask = mask_image

            # 创建一个空的Alpha图层
            alpha = Image.new("L", image.size, 255)
            # 将掩码B应用到Alpha图层
            alpha.paste(mask, (0, 0))
            # 将Alpha图层应用到图像A
            image.putalpha(alpha)
            # 保存带透明背景的图像
            png_byte_arr = io.BytesIO()
            image.save(png_byte_arr, format="PNG")
            png_byte_arr.seek(0)
            return png_byte_arr.getvalue()

        return _load_image_byte

    def _create_cache(self):
        # @lru_cache(maxsize=self.cache_size)
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=200))
        def _load_image(path):
            if not os.path.exists(path):
                return None
            img_byte_arr = io.BytesIO()
            image = Image.open(path)
            image.save(img_byte_arr, format='jpeg')
            img_byte_arr.seek(0)
            return img_byte_arr.getvalue()

        return _load_image

    def get_image(self, path, pil=False,clip_num=0):
        try:
            print(fr"getting image {path}")
            if pil:
                return self._cache_image_pil(path)
            if clip_num:
                return self._cache_image_clip(path, clip_num)
            return self._cache_image_byte(path)
        except Exception as e:
            print(f"Error loading image: {e}")
            return None

    def get_mask_image(self, path, mask_path):
        try:
            return self.mask_cache_image_byte(path, mask_path)
        except Exception as e:
            print(f"Error loading image: {e}")
            return None

    def clear_cache(self):
        self._cache.cache_clear()


class Data3dCache:
    def __init__(self, cache_size=16):
        self.cache_size = cache_size
        self._cache = self._create_cache()

    def _create_cache(self):
        # @lru_cache(maxsize=self.cache_size)
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=200))
        def _load_3d_data(path):
            if ".npy" in str(path):
                return np.load(path).astype(int)
            return np.load(path)["array"]

        return _load_3d_data

    def get_data(self, path):
        try:
            return self._cache(path)
        except Exception as e:
            print(f"Error loading data: {e}")
            return None

    def clear_cache(self):
        self._cache.cache_clear()


previewCache = ImageCache(256)
imageCache = ImageCache(128)

areaCache = ImageCache(32)

d3DataCache = Data3dCache(16)
classifierCache = ImageCache(100)
