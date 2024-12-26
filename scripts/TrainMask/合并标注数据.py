from pathlib import Path
import os
from tqdm import tqdm
import shutil


def join_files(from_folder, to_folder):
    for item in tqdm(from_folder.glob("*")):
        if item.is_dir():
            join_files(item, to_folder)
        else:
            try:
                shutil.copy(item, to_folder)
            except Exception as e:
                raise e

rootFolder = Path(fr"D:\样本\中间增加")
toFolder = Path(fr"D:\样本\中间增加_合并")
if toFolder.exists():
    shutil.rmtree(toFolder)
toFolder.mkdir(exist_ok=True)

join_files(rootFolder,toFolder)
