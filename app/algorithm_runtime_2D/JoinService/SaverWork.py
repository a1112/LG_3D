import gc
from io import BytesIO
from pathlib import Path
from queue import Queue

from PIL import Image

from configs.CameraConfig import CameraConfig
from configs.SurfaceConfig import SurfaceConfig
from utils.MultiprocessColorLogger import logger

from .WorkBase import WorkBaseThread

TILE_LEVELS = {
    0: (340, 60),
    1: (682, 70),
    2: (1364, 80),
    3: (2728, 90),
    4: (5460, 95),
}


class SaverWork(WorkBaseThread):
    def __init__(self, config: SurfaceConfig):
        super().__init__(config)
        self.queue_in = Queue(maxsize=1)
        self.config: SurfaceConfig = config
        self.size = (512, 512)
        self.tile_count = 3
        self._save_count = 0
        self.start()

    def save_thumbnail(self, url_, image):
        image.thumbnail(self.size)
        image.save(url_)

    def _tile_cache_base_dir(self, area_path: Path) -> Path:
        if area_path.parent.name in {"jpg", "png"}:
            coil_dir = area_path.parent.parent
        else:
            coil_dir = area_path.parent
        return coil_dir / "cache" / "area" / "tild"

    def _tile_cache_dir(self, area_path: Path, level: int = 4) -> Path:
        return self._tile_cache_base_dir(area_path) / f"L{level}"

    def _resize_tile_bytes(self, tile_image: Image.Image, target_size: int, quality: int) -> bytes:
        w, h = tile_image.size
        max_dim = max(w, h)
        if max_dim <= target_size:
            buf = BytesIO()
            tile_image.save(buf, format="JPEG", quality=quality)
            return buf.getvalue()

        scale = target_size / max_dim
        new_w = int(w * scale)
        new_h = int(h * scale)
        resized = tile_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        try:
            buf = BytesIO()
            resized.save(buf, format="JPEG", quality=quality)
            return buf.getvalue()
        finally:
            resized.close()

    def _write_tile_cache(self, area_path: Path, image: Image.Image) -> None:
        image_l = image.convert("L")
        try:
            width, height = image_l.size
            tile_width = width // self.tile_count
            tile_height = height // self.tile_count
            if tile_width <= 0 or tile_height <= 0:
                return

            cache_dirs = {}
            for level in TILE_LEVELS:
                cache_dir = self._tile_cache_dir(area_path, level)
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_dirs[level] = cache_dir

            for row in range(self.tile_count):
                for col in range(self.tile_count):
                    left = col * tile_width
                    top = row * tile_height
                    right = width if col == self.tile_count - 1 else left + tile_width
                    bottom = height if row == self.tile_count - 1 else top + tile_height
                    tile = image_l.crop((left, top, right, bottom))
                    try:
                        for level, (target_size, quality) in TILE_LEVELS.items():
                            tile_path = cache_dirs[level] / f"{col}_{row}.jpg"
                            if level == 4:
                                tile.save(tile_path, quality=quality)
                            else:
                                tile_path.write_bytes(self._resize_tile_bytes(tile, target_size, quality))
                    finally:
                        tile.close()
            logger.debug("Saved AREA tiles to %s", self._tile_cache_base_dir(area_path))
        finally:
            image_l.close()

    def run(self):
        while self.__run__:
            image = None
            try:
                coil_id, image = self.queue_in.get()
                image = Image.fromarray(image)
                save_f = self.config.get_area_url(coil_id)
                save_f.parent.mkdir(parents=True, exist_ok=True)
                save_t = self.config.get_area_url_pre(coil_id)
                save_t.parent.mkdir(parents=True, exist_ok=True)
                logger.debug("2D AREA saving: %s", save_f)
                image.save(save_f)
                self._write_tile_cache(save_f, image)
                self.save_thumbnail(save_t, image)
                logger.info("2D AREA saved: %s", save_f)
            except Exception as e:
                logger.exception("2D AREA save failed: %s", e)
            finally:
                if image is not None:
                    try:
                        image.close()
                    except Exception as e:
                        logger.debug("2D AREA image close failed: %s", e)
                self._save_count += 1
                if self._save_count % 20 == 0:
                    gc.collect()


class DebugSaveWork(WorkBaseThread):
    def __init__(self, config):
        self.config: CameraConfig = config
        self.image_save_folder = Path("D:/AreaSaveFolder")
        self.image_save_folder.mkdir(parents=True, exist_ok=True)
        super().__init__(config)
        self.start()

    def run(self):
        while self._run_:
            image = None
            try:
                coil_id, camera_key, index, image = self.queue_in.get()
                save_f = self.image_save_folder / f"{camera_key}_{coil_id}_{index}.jpg"
                image.thumbnail((1024, 1024))
                image.save(save_f)
            except Exception as e:
                logger.exception("2D debug image save failed: %s", e)
            finally:
                if image is not None:
                    try:
                        image.close()
                    except Exception as e:
                        logger.debug("2D debug image close failed: %s", e)
