import logging
import shutil
from pathlib import Path

from tqdm import tqdm

from CoilDataBase import Coil

logger = logging.getLogger(__name__)


def move_has_defect_clip_images(
        source_folder: Path = Path("j:/cropped_moved_2"),
        save_folder: Path = Path("j:/cropped_moved_3"),
) -> None:
    file_list = list(source_folder.glob("*.jpg"))
    logger.info("found %s jpg files in %s", len(file_list), source_folder)
    save_folder.mkdir(parents=True, exist_ok=True)
    coil_set = {item.secondaryCoilId for item in Coil.defects() if item.defectName in ["鎶樺彔"]}

    for file in tqdm(file_list):
        coil_id = int(file.stem.split("_")[1])
        if coil_id in coil_set:
            shutil.copy(file, save_folder / file.name)
            image_url = file.with_suffix(".jpg")
            shutil.copy(image_url, save_folder / image_url.name)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    move_has_defect_clip_images()
