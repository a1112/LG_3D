from pathlib import Path
import json
import os
import cv2
import shutil
import tqdm
toFolder = Path(r"E:\Copy")
toFolder.mkdir(exist_ok=True)
for coil_index in tqdm.tqdm(range(92803, 92853)):
    for folder in [
        "F:/Cap_L_D", "F:\Cap_L_U", "F:/Cap_L_M",
        "G:/Cap_S_U", "G:/Cap_S_D", "G:/Cap_S_M"
    ]:
        folder = Path(folder)
        folderName = folder.name
        fromFolder = folder / f"{coil_index}"
        if not fromFolder.exists():
            continue
        toF = toFolder / folderName/ f"{coil_index}"
        toF.parent.mkdir(exist_ok=True,parents=True)
        # toFolder = toF
        try:
            shutil.copytree(fromFolder, toF)
        except:
            pass