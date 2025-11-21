import socket
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


if socket.gethostname() == "lcx_ace":
    rootFolder = Path(fr"F:\subImage\样本")
    toFolder = rootFolder.parent / "样本_合并"
    if toFolder.exists():
        shutil.rmtree(toFolder)
    toFolder.mkdir(exist_ok=True)

    join_files(rootFolder, toFolder)
