import logging
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)


def rmDir(path: Path):
    path= Path(path)

    if path.is_dir():
        for subDir in path.iterdir():
            try:
                if int(subDir.stem) < 1750:
                    logger.info("delete %s", subDir)
                    shutil.rmtree(str(subDir))
            except ValueError:
                continue
            except OSError as e:
                logger.warning("delete %s failed: %s", subDir, e)


if __name__ == "__main__":
    for folder in [fr"F:\datasets\LG_3D_DataBase\DataSave"]:
        for itemFolder in Path(folder).iterdir():
            rmDir(itemFolder)
