from pathlib import Path
import shutil
from PIL import Image

from configs.CameraConfig import CameraConfig
from configs.SurfaceConfig import SurfaceConfig
from utils.MultiprocessColorLogger import logger
from .WorkBase import WorkBaseThread

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

    def _tile_cache_dir(self, area_path: Path) -> Path:
        if area_path.parent.name in {"jpg", "png"}:
            coil_dir = area_path.parent.parent
        else:
            coil_dir = area_path.parent
        return coil_dir / "cache" / "area" / "tild"

    def _write_tile_cache(self, area_path: Path, image: Image.Image) -> None:
        cache_dir = self._tile_cache_dir(area_path)
        if cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

        image_l = image.convert("L")
        width, height = image_l.size
        w_width = width // self.tile_count
        h_height = height // self.tile_count
        if w_width <= 0 or h_height <= 0:
            return
        for row in range(self.tile_count):
            for col in range(self.tile_count):
                left = row * w_width
                top = col * h_height
                right = left + w_width
                bottom = top + h_height
                tile = image_l.crop((left, top, right, bottom))
                tile.save(cache_dir / f"{col}_{row}.jpg")

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
