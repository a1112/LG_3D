from pathlib import Path
import json
import os
import cv2
import shutil

toFolder = Path(r"F:\Copy")
toFolder.mkdir(exist_ok=True)
for coil_index in range(1001, 1100):
    for folder in [
        "F:/Cap_L_D", "F/Cap_L_U", "F:/Cap_L_M",
        "G:/Cap_S_U", "G:/Cap_S_D", "G:/Cap_S_M"
    ]:
        folder = Path(folder)
        folderName = folder.name
        fromFolder = folder / f"{coil_index}"
        if not fromFolder.exists():
            continue
        toF = toFolder / folderName
        toF.mkdir(exist_ok=True)
        # toFolder = toF / f"{coil_index}"
        shutil.copytree(fromFolder, toFolder)
