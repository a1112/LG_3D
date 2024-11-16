import os
import time
from pathlib import Path
from threading import Thread
from PIL import Image
import shutil
import numpy as np


class ZipAndDeletion(Thread):
    def __init__(self, path: Path):
        self.path = path
        super().__init__()

    def run(self):
        folders = list(self.path.iterdir())
        for folder in folders:
            print(folder)
            imageFolder = folder / "2D"
            for imageUrl in imageFolder.glob("*.bmp"):
                image=Image.open(imageUrl)
                image.save(imageUrl.with_suffix(".jpg"),quality=95, optimize=True)
                image.close()
                os.remove(str(imageUrl))
            d3Folder = folder / "3D"
            for d3Url in d3Folder.glob("*.npy"):
                d3 = np.load(d3Url)
                np.savez_compressed(d3Url.with_suffix(".npz"),array=d3)
                os.remove(str(d3Url))


    def zip_bmp(self,bmp_url):
        image = Image.open(bmp_url)
        image.save(bmp_url.with_suffix(".jpg"))
        image.close()
        os.remove(str(bmp_url))

    def zip_npy(self,npy_url):
        npy = np.load(npy_url)
        np.savez_compressed(npy_url.with_suffix(".npz"),array=npy)
        os.remove(str(npy_url))

    def delete(self):
        pass


if __name__ == '__main__':
    ZipAndDeletion(Path(r"F:\Cap_L_D")).start()
    ZipAndDeletion(Path(r"F:\Cap_L_U")).start()
    ZipAndDeletion(Path(r"F:\Cap_L_M")).start()
    ZipAndDeletion(Path(r"G:\Cap_S_U")).start()
    ZipAndDeletion(Path(r"G:\Cap_S_M")).start()
    ZipAndDeletion(Path(r"G:\Cap_S_D")).start()