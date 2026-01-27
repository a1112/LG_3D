from pathlib import Path
import shutil
from collections import defaultdict
from PIL import Image

from configs.CameraConfig import CameraConfig
from configs.SurfaceConfig import SurfaceConfig
from utils.MultiprocessColorLogger import logger
from .WorkBase import WorkBaseThread

# 多级瓦片配置：级别 -> (目标尺寸, JPEG质量)
TILE_LEVELS = {
    0: (340, 60),    # Level 0: 1/16 缩略图 (~20KB)
    1: (682, 70),    # Level 1: 1/8 (~50KB)
    2: (1364, 80),   # Level 2: 1/4 (~120KB)
    3: (2728, 90),   # Level 3: 1/2 (~250KB)
    4: (5460, 95),   # Level 4: 原图瓦片 (~500KB)
}

class SaverWork(WorkBaseThread):
    def __init__(self,config:SurfaceConfig):
        super().__init__(config)
        self.start()
        self.config:SurfaceConfig
        self.size = (512, 512)
        self.tile_count = 3

    def save_thumbnail(self,url_,image):
        image.thumbnail(self.size)
        # if CONFIG.DEBUG:
        #     image.show()
        image.save(url_)

    def _tile_cache_base_dir(self, area_path: Path) -> Path:
        """获取瓦片缓存基础目录"""
        if area_path.parent.name in {"jpg", "png"}:
            coil_dir = area_path.parent.parent
        else:
            coil_dir = area_path.parent
        return coil_dir / "cache" / "area" / "tild"

    def _tile_cache_dir(self, area_path: Path, level: int = 4) -> Path:
        """获取指定级别的瓦片缓存目录"""
        # 按级别分目录: cache/area/tild/L0/, L1/, L2/, etc.
        return self._tile_cache_base_dir(area_path) / f"L{level}"

    def _resize_tile_bytes(self, tile_image: Image.Image, target_size: int, quality: int) -> bytes:
        """调整瓦片尺寸并返回 bytes"""
        w, h = tile_image.size
        max_dim = max(w, h)

        if max_dim <= target_size:
            # 不需要缩小，只调整质量
            from io import BytesIO
            buf = BytesIO()
            tile_image.save(buf, format="JPEG", quality=quality)
            return buf.getvalue()

        # 缩小图像
        scale = target_size / max_dim
        new_w = int(w * scale)
        new_h = int(h * scale)
        resized = tile_image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        from io import BytesIO
        buf = BytesIO()
        resized.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

    def _write_tile_cache(self, area_path: Path, image: Image.Image) -> None:
        """生成多级瓦片缓存 (L0-L4)"""
        # 转换为灰度图
        image_l = image.convert("L")
        width, height = image_l.size
        w_width = width // self.tile_count
        h_height = height // self.tile_count
        if w_width <= 0 or h_height <= 0:
            return

        # 先生成 L4 原图瓦片
        l4_tiles = defaultdict(dict)
        for row in range(self.tile_count):
            for col in range(self.tile_count):
                left = row * w_width
                top = col * h_height
                right = left + w_width
                bottom = top + h_height
                tile = image_l.crop((left, top, right, bottom))
                l4_tiles[col][row] = tile

        # 保存 L4 瓦片
        l4_cache_dir = self._tile_cache_dir(area_path, 4)
        l4_cache_dir.mkdir(parents=True, exist_ok=True)
        for col in l4_tiles:
            for row in l4_tiles[col]:
                tile_path = l4_cache_dir / f"{col}_{row}.jpg"
                l4_tiles[col][row].save(tile_path, quality=TILE_LEVELS[4][1])
        logger.info(f"Saved L4 tiles to {l4_cache_dir}")

        # 同时生成并保存 L0-L3 瓦片
        for level in range(4):
            target_size, quality = TILE_LEVELS[level]
            level_cache_dir = self._tile_cache_dir(area_path, level)
            level_cache_dir.mkdir(parents=True, exist_ok=True)

            for col in l4_tiles:
                for row in l4_tiles[col]:
                    # 调整尺寸并保存
                    resized_bytes = self._resize_tile_bytes(l4_tiles[col][row], target_size, quality)
                    tile_path = level_cache_dir / f"{col}_{row}.jpg"
                    tile_path.write_bytes(resized_bytes)
            logger.info(f"Saved L{level} tiles to {level_cache_dir}")

    def run(self):
        while self.__run__:
            try:
                coil_id, image = self.queue_in.get()
                image = Image.fromarray(image)
                save_f = self.config.get_area_url(coil_id)
                save_f.parent.mkdir(parents=True, exist_ok=True)
                save_t = self.config.get_area_url_pre(coil_id)
                save_t.parent.mkdir(parents=True, exist_ok=True)
                logger.debug(fr"图像保存： {save_f}")
                image.save(save_f)
                # 生成 AREA 多级瓦片缓存 (L0-L4)
                self._write_tile_cache(save_f, image)
                self.save_thumbnail(save_t,image)
            except BaseException as e:
                print(e)


class DebugSaveWork(WorkBaseThread):
    """
    保存用来识别模型的数据

    """
    def __init__(self,config):
        self.config:CameraConfig = config
        self.image_save_folder = Path(fr"D:\AreaSaveFolder")
        self.image_save_folder.mkdir(parents=True, exist_ok=True)
        super().__init__(config)
        self.start()

    def run(self):
        while self._run_:
            coil_id, camera_key, index, image = self.queue_in.get()
            save_f = self.image_save_folder / fr"{camera_key}_{coil_id}_{index}.jpg"
            image.thumbnail((1024, 1024))
            image.save(save_f)
