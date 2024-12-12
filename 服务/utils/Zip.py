import os
import time
from pathlib import Path
from PIL import Image
import numpy as np

import Globs


def _zip_(folder):
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


class ZipAndDeletionCameraData(Globs.ProcessClass):
    def __init__(self, path: Path, reserve_num=0):
        print(path)
        self.path = Path(path)
        self.reserve_num = reserve_num
        super().__init__()

    def run(self):
        while self._run_:
            folders = list(self.path.iterdir())
            for folder in folders[self.reserve_num:][::-1]:
                try:
                    s_time = time.time()
                    zip_state = _zip_(folder)
                    e_time = time.time()
                    if zip_state:
                        print(f"{zip_state} {folder} 数据压缩成功! 耗时: {e_time - s_time}")
                except Exception as e:
                    print(f"数据压缩失败! {e}")
            print(f"{self.path} 压缩完成")
            time.sleep(6000)

    def delete(self):
        pass


if __name__ == '__main__':
    ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_L_D")).start()
    ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_L_U")).start()
    ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_L_M")).start()
    ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_S_U")).start()
    ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_S_M")).start()
    ZipAndDeletionCameraData(Path(r"G:\BF_DATA\Cap_S_D")).start()
