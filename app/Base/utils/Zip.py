import logging
import os
import time
from pathlib import Path
from PIL import Image
import numpy as np

from Base import Globs

logger = logging.getLogger(__name__)

MIN_COMPRESS_AGE_SECONDS = 10 * 60


def _folder_sort_key(folder: Path) -> tuple[int, str]:
    try:
        return int(folder.name), folder.name
    except ValueError:
        try:
            return int(folder.stat().st_mtime), folder.name
        except OSError:
            return 0, folder.name


def _old_folders(path: Path, reserve_num: int) -> list[Path]:
    if not path.exists():
        logger.debug("compression path does not exist: %s", path)
        return []
    folders = [folder for folder in path.iterdir() if folder.is_dir()]
    folders.sort(key=_folder_sort_key, reverse=True)
    return folders[reserve_num:]


def _resolve_child_dir(folder: Path, dir_name: str) -> Path:
    candidate = folder / dir_name
    if candidate.exists():
        return candidate
    lowered_name = dir_name.lower()
    try:
        for child in folder.iterdir():
            if child.is_dir() and child.name.lower() == lowered_name:
                return child
    except OSError:
        pass
    return candidate


def _latest_mtime(folder: Path) -> float:
    latest = folder.stat().st_mtime
    for child_path in folder.iterdir():
        try:
            latest = max(latest, child_path.stat().st_mtime)
            if child_path.is_dir():
                for child in child_path.iterdir():
                    latest = max(latest, child.stat().st_mtime)
        except OSError:
            return time.time()
    return latest


def _is_quiet_folder(folder: Path) -> bool:
    try:
        return time.time() - _latest_mtime(folder) >= MIN_COMPRESS_AGE_SECONDS
    except OSError:
        return False


def _is_file_access_error(error: Exception) -> bool:
    return isinstance(error, PermissionError) or getattr(error, "winerror",
                                                        None) == 32


def _zip_camera_data_(folder):
    if not _is_quiet_folder(folder):
        return False

    image_folder = _resolve_child_dir(folder, "2D")
    bmp_list = list(image_folder.glob("*.bmp"))
    if not len(bmp_list):
        time.sleep(0.001)
        return False
    compressed = False
    for imageUrl in bmp_list:
        try:
            with Image.open(imageUrl) as image:
                image.load()
                image.save(imageUrl.with_suffix(".jpg"),
                           quality=95,
                           optimize=True)
            os.remove(str(imageUrl))
            compressed = True
        except Exception as e:
            if _is_file_access_error(e):
                logger.debug("skip busy camera data folder %s: %s %s", folder, imageUrl, e)
                return False
            logger.warning("skip uncompressible 2D image %s: %s", imageUrl, e)
            continue
    d3_folder = _resolve_child_dir(folder, "3D")
    for d3Url in d3_folder.glob("*.npy"):
        try:
            d3 = np.load(d3Url)
            np.savez_compressed(d3Url.with_suffix(".npz"), array=d3)
            os.remove(str(d3Url))
            compressed = True
        except Exception as e:
            if _is_file_access_error(e):
                logger.debug("skip busy 3D data folder %s: %s %s", folder, d3Url, e)
                return False
            logger.warning("skip uncompressible 3D data %s: %s", d3Url, e)
    return compressed

def _zip_save_data_(folder):
    if not _is_quiet_folder(folder):
        return False

    obj_file = folder / "3D.obj"
    if obj_file.exists():
        try:
            os.remove(str(obj_file))
        except Exception as e:
            if _is_file_access_error(e):
                return False
            raise
    npy_file = folder / "3D.npy"
    if npy_file.exists():
        try:
            d3 = np.load(npy_file)
            np.savez_compressed(npy_file.with_suffix(".npz"), array=d3)
            os.remove(str(npy_file))
        except Exception as e:
            if _is_file_access_error(e):
                return False
            raise
    else:
        return False
    return True

def _archive_(folder):
    image_folder = folder / "2D"
    image_list = list(image_folder.glob("*.*"))
    if not len(image_list):
        time.sleep(0.001)
        return False
    image_array_list = [np.array(Image.open(imageUrl)) for imageUrl in image_list]
    d3_folder = folder / "3D"
    d3_array_list = [np.load(d3Url) for d3Url in list(d3_folder.glob("*.npy"))] + \
    [np.load(d3Url)["array"] for d3Url in list(d3_folder.glob("*.npz"))]
    np.savez_compressed(str(folder/"archive.npz"), image_array_list=image_array_list)
    logger.debug("archived image arrays: %s", len(image_array_list))
    logger.debug("archived 3D arrays: %s", len(d3_array_list))


class ZipAndDeletionCameraData(Globs.control.SaveAndDeleteCameraDataBase):
    def __init__(self, path: Path, reserve_num=0):
        self._run_ = True
        self.path = Path(path)
        self.reserve_num = reserve_num
        super().__init__()

    def run(self):
        while self._run_:
            for folder in _old_folders(self.path, self.reserve_num)[::-1]:
                try:
                    s_time = time.time()
                    zip_state = _zip_camera_data_(folder)
                    e_time = time.time()
                    if zip_state:
                        logger.info("camera data compressed: %s elapsed=%.3fs", folder, e_time - s_time)
                except Exception as e:
                    logger.exception("camera data compression failed: %s", e)
            logger.debug("camera compression pass finished: %s", self.path)
            time.sleep(6000)

    def delete(self):
        pass


class ZipAndDeletionSaveData(Globs.control.SaveAndDeleteSaveDataBase):
    def __init__(self, path: Path, reserve_num=0):
        """
        对保存的数据进行商储
        """
        self._run_ = True
        self.path = Path(path)
        self.reserve_num = reserve_num
        super().__init__()

    def run(self):
        while self._run_:
            for folder in _old_folders(self.path, self.reserve_num)[::-1]:
                try:
                    s_time = time.time()
                    zip_state = _zip_save_data_(folder)
                    e_time = time.time()
                    if zip_state:
                        logger.info("saved data compressed: %s elapsed=%.3fs", folder, e_time - s_time)
                except Exception as e:
                    logger.exception("saved data compression failed: %s", e)
            logger.debug("saved data compression pass finished: %s", self.path)
            time.sleep(6000)


if __name__ == '__main__':
    _archive_(Path(fr"F:\datasets\LG_3D_DataBase\COPY\Cap_S_M\1792"))
    # ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_L_D")).start()
    # ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_L_U")).start()
    # ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_L_M")).start()
    # ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_S_U")).start()
    # ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_S_M")).start()
    # ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_S_D")).start()
