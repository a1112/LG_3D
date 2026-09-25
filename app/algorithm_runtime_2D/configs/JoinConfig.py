import heapq
import logging
import os
from pathlib import Path
from threading import Lock

from .BaseConfig import BaseConfig
from .SurfaceConfig import SurfaceConfig


log = logging.getLogger(__name__)

def sort_folder(image_url_list):
    image_url_list = [item for item in image_url_list if Path(item).stem.isdigit()]
    image_url_list.sort(key=lambda i: int(Path(i).stem),reverse = True)
    return image_url_list


def _numeric_folder_ids(folder: Path) -> list[int]:
    ids = []
    try:
        with os.scandir(folder) as entries:
            for entry in entries:
                if entry.name.isdigit() and entry.is_dir(follow_symlinks=False):
                    ids.append(int(entry.name))
    except OSError as e:
        log.warning("source folder scan failed: %s error=%s", folder, e)
    return ids

class JoinConfig(BaseConfig):
    def __init__(self, file_):
        super().__init__(file_)
        self._source_folder_cache = {}
        self._source_folder_cache_lock = Lock()
        self.surfaces = {
            surface_key: SurfaceConfig(surface_key,config)
            for surface_key, config in self.config["surfaces"].items()
        }

    def _source_folder_ids(self, folder: Path) -> tuple[int, ...]:
        try:
            modified_ns = folder.stat().st_mtime_ns
        except OSError:
            return ()

        with self._source_folder_cache_lock:
            cached = self._source_folder_cache.get(folder)
            if cached is not None and cached[0] == modified_ns:
                return cached[1]

        ids = tuple(sorted(_numeric_folder_ids(folder), reverse=True))
        with self._source_folder_cache_lock:
            self._source_folder_cache[folder] = (modified_ns, ids)
        log.debug("2D source folder refreshed: folder=%s count=%s", folder, len(ids))
        return ids

    def _source_id_lists(self) -> list[tuple[int, ...]]:
        return [
            self._source_folder_ids(camera_config.folder)
            for surface in self.surfaces.values()
            for camera_config in surface.camera_configs
        ]

    def get_source_coil_ids(self, limit: int) -> list[int]:
        if limit <= 0:
            return []
        id_lists = [ids for ids in self._source_id_lists() if ids]
        if not id_lists:
            return []

        result = []
        previous = None
        for coil_id in heapq.merge(*id_lists, reverse=True):
            if coil_id == previous:
                continue
            result.append(coil_id)
            previous = coil_id
            if len(result) >= limit:
                break
        return result

    def get_source_min_coil(self):
        minimums = [ids[-1] for ids in self._source_id_lists() if ids]
        return min(minimums) if minimums else 0


    def get_source_max_coil(self):
        ids = self.get_source_coil_ids(1)
        return ids[0] if ids else 0

    def get_save_min_coil(self):
        try:
            surface = list(self.surfaces.values())[0]
            save_folder1 = Path(surface.save_folder)
            folders = list(save_folder1.iterdir())
            folders = sort_folder(folders)
            return int(folders[-1].stem)
        except IndexError:
            return 0

    def get_save_max_coil(self):
        try:
            surface = list(self.surfaces.values())[0]
            save_folder1 = Path(surface.save_folder)
            folders = list(save_folder1.iterdir())
            folders = sort_folder(folders)
            return int(folders[0].stem)
        except IndexError:
            return 0

    def get_last_coil(self):

        surface = list(self.surfaces.values())[0]
        save_folder1 = Path(surface.save_folder)
        folders = list(save_folder1.iterdir())
        folders = sort_folder(folders)
        # folders = folders[start_coil:]
        for f in folders:
            coil_id = f.stem
            if surface.get_area_url(coil_id).exists():
                return coil_id
        return int(folders[-1].stem)

    def can_(self,coil_id):
        coil_id = int(coil_id)
        for surface in self.surfaces.values():
            if surface.get_area_url(coil_id).parent.parent.exists() and \
                    surface.get_area_url(coil_id + 1).parent.parent.exists():
                return True
        return False

