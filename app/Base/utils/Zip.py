import os
import time
from pathlib import Path
from PIL import Image
import numpy as np

from Base import Globs


def _zip_camera_data_(folder):
    image_folder = folder / "2D"
    bmp_list = list(image_folder.glob("*.bmp"))
    if not len(bmp_list):
        time.sleep(0.001)
        return False
    for imageUrl in bmp_list:
        image = Image.open(imageUrl)
        image.save(imageUrl.with_suffix(".jpg"), quality=95, optimize=True)
        image.close()
        os.remove(str(imageUrl))
    d3_folder = folder / "3D"
    for d3Url in d3_folder.glob("*.npy"):
        d3 = np.load(d3Url)
        np.savez_compressed(d3Url.with_suffix(".npz"), array=d3)
        os.remove(str(d3Url))
    return True

def _zip_save_data_(folder):
    obj_file = folder / "3D.obj"
    if obj_file.exists():
        os.remove(str(obj_file))
    npy_file = folder / "3D.npy"
    if npy_file.exists():
        d3 = np.load(npy_file)
        np.savez_compressed(npy_file.with_suffix(".npz"), array=d3)
        os.remove(str(npy_file))
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
    print(image_array_list)
    print(d3_array_list)


class ZipAndDeletionCameraData(Globs.control.SaveAndDeleteCameraDataBase):
    def __init__(self, path: Path, reserve_num=0):
        self._run_ = True
        self.path = Path(path)
        self.reserve_num = reserve_num
        super().__init__()

    def run(self):
        while self._run_:
            folders = list(self.path.iterdir())
            for folder in folders[self.reserve_num:][::-1]:
                try:
                    s_time = time.time()
                    zip_state = _zip_camera_data_(folder)
                    e_time = time.time()
                    if zip_state:
                        print(f"{zip_state} {folder} 数据压缩成功! 耗时: {e_time - s_time}")
                except Exception as e:
                    print(f"数据压缩失败! {e}")
            print(f"{self.path} 压缩完成")
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
            folders = list(self.path.iterdir())
            for folder in folders[self.reserve_num:][::-1]:
                try:
                    s_time = time.time()
                    zip_state = _zip_save_data_(folder)
                    e_time = time.time()
                    if zip_state:
                        print(f"{zip_state} {folder} 数据压缩成功! 耗时: {e_time - s_time}")
                except Exception as e:
                    pass


if __name__ == '__main__':
    _archive_(Path(fr"F:\datasets\LG_3D_DataBase\COPY\Cap_S_M\1792"))
    # ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_L_D")).start()
    # ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_L_U")).start()
    # ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_L_M")).start()
    # ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_S_U")).start()
    # ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_S_M")).start()
    # ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_S_D")).start()
