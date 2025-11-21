from pathlib import Path
import json
import os
import shutil

fromPath = Path(r"I:\database\2D")
toPath = Path(r"I:\database\2D_train")
toPath.mkdir(exist_ok=True, parents=True)
for xmlFile in fromPath.glob("*.xml"):
    pngFile = xmlFile.with_suffix(".png")
    shutil.copy(pngFile, toPath)
    shutil.copy(xmlFile, toPath)
