from pathlib import Path
import shutil


def rmDir(path: Path):
    path= Path(path)

    if path.is_dir():
        for subDir in path.iterdir():
            try:
                if int(subDir.stem) < 1750:
                    print(fr"delete {subDir}")
                    shutil.rmtree(str(subDir))
            except:
                pass


for folder in [fr"F:\datasets\LG_3D_DataBase\DataSave"]:
    for itemFolder in Path(folder).iterdir():
        rmDir(itemFolder)