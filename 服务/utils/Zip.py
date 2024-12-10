import os
import time
from pathlib import Path
from PIL import Image
import numpy as np

import Globs


def _zip_(folder):
    imageFolder = folder / "2D"
    bmpList = list(imageFolder.glob("*.bmp"))
    if not len(bmpList):
        time.sleep(0.001)
        return False
    for imageUrl in bmpList:
        image = Image.open(imageUrl)
        image.save(imageUrl.with_suffix(".jpg"), quality=95, optimize=True)
        image.close()
        os.remove(str(imageUrl))
    d3Folder = folder / "3D"
    for d3Url in d3Folder.glob("*.npy"):
        d3 = np.load(d3Url)
        np.savez_compressed(d3Url.with_suffix(".npz"), array=d3)
        os.remove(str(d3Url))
    return True


class ZipAndDeletion(Globs.ProcessClass):
    def __init__(self, path: Path, reserve_num=0):
        print(path)
        self.path = Path(path)
        self.reserve_num = reserve_num
        super().__init__()

    def run(self):
        folders = list(self.path.iterdir())
        for folder in folders[self.reserve_num:][::-1]:
            try:
                sTime = time.time()
                zipState = _zip_(folder)
                eTime = time.time()
                if zipState:
                    print(f"{zipState} {folder} 数据压缩成功! 耗时: {eTime - sTime}")
            except Exception as e:
                print(f"数据压缩失败! {e}")
        time.sleep(100)

    def delete(self):
        pass


if __name__ == '__main__':
    ZipAndDeletion(Path(r"F:\Cap_L_D")).start()
    ZipAndDeletion(Path(r"F:\Cap_L_U")).start()
    ZipAndDeletion(Path(r"F:\Cap_L_M")).start()
    ZipAndDeletion(Path(r"G:\Cap_S_U")).start()
    ZipAndDeletion(Path(r"G:\Cap_S_M")).start()
    ZipAndDeletion(Path(r"G:\Cap_S_D")).start()
