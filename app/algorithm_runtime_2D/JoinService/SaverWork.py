import gc
from io import BytesIO
from pathlib import Path
from queue import Queue

import numpy as np
from PIL import Image

from algorithm_runtime_2D.configs.CameraConfig import CameraConfig
from algorithm_runtime_2D.configs.SurfaceConfig import SurfaceConfig
from algorithm_runtime_2D.utils.MultiprocessColorLogger import logger

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
        super().__init__(config, deduplicate=True)
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
        if area_path.stem.upper() != "AREA":
            return coil_dir / "cache" / "area" / area_path.stem.upper() / "tild"
        return coil_dir / "cache" / "area" / "tild"

    def _tile_cache_dir(self, area_path: Path, level: int = 4) -> Path:
        return self._tile_cache_base_dir(area_path) / f"L{level}"

    def _state_markers(self, coil_id) -> tuple[Path, Path]:
        if hasattr(self.config, "get_area_completion_marker"):
            completion_marker = self.config.get_area_completion_marker(coil_id)
            in_progress_marker = self.config.get_area_in_progress_marker(coil_id)
        else:
            coil_folder = self.config.get_area_url(coil_id).parent.parent
            completion_marker = coil_folder / ".area_complete"
            in_progress_marker = coil_folder / ".area_in_progress"
        return completion_marker, in_progress_marker

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
        width, height = image.size
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
                tile = image.crop((left, top, right, bottom))
                if tile.mode != "L":
                    gray_tile = tile.convert("L")
                    tile.close()
                    tile = gray_tile
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

    @staticmethod
    def _mask_image_from_array(mask_array) -> Image.Image | None:
        if mask_array is None:
            return None
        mask_array = np.asarray(mask_array)
        if mask_array.size == 0:
            return None
        if mask_array.ndim == 3:
            mask_array = mask_array.max(axis=2)
        mask_array = np.asarray(mask_array, dtype=np.uint8)
        if mask_array.size and mask_array.max() <= 1:
            mask_array = mask_array * 255
        return Image.fromarray(mask_array)

    def _save_area_image(self, coil_id, image: Image.Image, name: str) -> None:
        save_f = self.config.get_area_url(coil_id, name)
        save_f.parent.mkdir(parents=True, exist_ok=True)
        save_t = self.config.get_area_url_pre(coil_id, name)
        save_t.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("2D %s saving: %s", name, save_f)
        temporary_image = save_f.with_name(f"{save_f.name}.tmp")
        temporary_image.unlink(missing_ok=True)
        image.save(temporary_image, format="JPEG")
        temporary_image.replace(save_f)
        self._write_tile_cache(save_f, image)
        image.thumbnail(self.size)
        temporary_preview = save_t.with_name(f"{save_t.name}.tmp")
        temporary_preview.unlink(missing_ok=True)
        image.save(temporary_preview, format="JPEG")
        temporary_preview.replace(save_t)
        logger.info("2D %s saved: %s", name, save_f)

    def run(self):
        while True:
            image = None
            mask_image = None
            mask_array = None
            work_item = None
            work_request = self.get_next_work()
            if work_request is None:
                break
            work_item = self.get_work_value(work_request)
            self.mark_started(work_request)
            try:
                if len(work_item) == 2:
                    coil_id, image = work_item
                    mask_array = None
                else:
                    coil_id, image, mask_array = work_item
                completion_marker, in_progress_marker = self._state_markers(coil_id)
                completion_marker.parent.mkdir(parents=True, exist_ok=True)
                completion_marker.unlink(missing_ok=True)
                in_progress_marker.write_text("saving", encoding="utf-8")
                source_image_array = image
                image = Image.fromarray(source_image_array)
                if isinstance(work_item, list):
                    work_item[1] = None
                source_image_array = None
                self._save_area_image(coil_id, image, "AREA")
                mask_image = self._mask_image_from_array(mask_array)
                if isinstance(work_item, list) and len(work_item) > 2:
                    work_item[2] = None
                mask_array = None
                if mask_image is not None:
                    self._save_area_image(coil_id, mask_image, "AREA_MASK")
                temporary_marker = completion_marker.with_name(f"{completion_marker.name}.tmp")
                temporary_marker.write_text("complete", encoding="utf-8")
                temporary_marker.replace(completion_marker)
                in_progress_marker.unlink(missing_ok=True)
            except Exception as e:
                logger.exception("2D AREA save failed: %s", e)
            finally:
                if image is not None:
                    try:
                        image.close()
                    except Exception as e:
                        logger.debug("2D AREA image close failed: %s", e)
                if mask_image is not None:
                    try:
                        mask_image.close()
                    except Exception as e:
                        logger.debug("2D AREA_MASK image close failed: %s", e)
                self.mark_finished(work_request)
                self.queue_in.task_done()
                mask_array = None
                work_item = None
                work_request = None
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
        while True:
            image = None
            work_request = self.get_next_work()
            if work_request is None:
                break
            work_item = self.get_work_value(work_request)
            self.mark_started(work_request)
            try:
                coil_id, camera_key, index, image = work_item
                save_f = self.image_save_folder / f"{camera_key}_{coil_id}_{index}.jpg"
                if isinstance(image, np.ndarray):
                    image = Image.fromarray(image)
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
                self.mark_finished(work_request)
                self.queue_in.task_done()
