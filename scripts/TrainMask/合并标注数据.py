from pathlib import Path
import os
from tqdm import tqdm
import shutil


def join_files(fromFolder, toFolder):
    for item in tqdm(fromFolder.glob("*")):
        if item.is_dir():
            join_files(item, toFolder)
        else:
            try:
                shutil.copy(item, toFolder)
            except Exception as e:
                raise e

rootFolder = Path(fr"D:\样本\中间增加")
toFolder = Path(fr"D:\样本\中间增加_合并")
if toFolder.exists():
    shutil.rmtree(toFolder)
toFolder.mkdir(exist_ok=True)

join_files(rootFolder,toFolder)