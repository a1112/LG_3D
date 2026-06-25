import logging
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

SAVE_FOLDER = Path(r"E:\clip_2D")
SOURCE_FOLDERS = [Path(r"D:\Save_S"), Path(r"E:\Save_L")]
MAX_COIL_ID = 8517
GRID_SIZE = 10


def clip_surface_images(save_folder: Path = SAVE_FOLDER) -> None:
    save_folder.mkdir(exist_ok=True)
    for folder in SOURCE_FOLDERS:
        if not folder.exists():
            logger.debug("source folder does not exist: %s", folder)
            continue
        for item_folder in folder.iterdir():
            try:
                coil_id = int(item_folder.name)
            except ValueError:
                continue
            if coil_id > MAX_COIL_ID:
                continue
            try:
                logger.debug("clip surface image folder: %s", item_folder)
                gray_image = np.asarray(Image.open(item_folder / "GRAY.png"))
                mask_image = np.asarray(Image.open(item_folder / "MASK.png"))
                h_item_size = mask_image.shape[0] // GRID_SIZE
                w_item_size = mask_image.shape[1] // GRID_SIZE
                surface_key = item_folder.parent.name[-1]
                for i in range(GRID_SIZE):
                    for j in range(GRID_SIZE):
                        x, y, w, h = (
                            w_item_size * j,
                            h_item_size * i,
                            w_item_size,
                            h_item_size,
                        )
                        clip_image = gray_image[h_item_size * i:h_item_size * (i + 1),
                                               w_item_size * j:w_item_size * (j + 1)]
                        clip_mask = mask_image[h_item_size * i:h_item_size * (i + 1),
                                               w_item_size * j:w_item_size * (j + 1)]
                        if np.count_nonzero(clip_mask) / (clip_mask.shape[0] * clip_mask.shape[1]) <= 0.3:
                            continue
                        if h < 300 or w < 300:
                            continue
                        save_name = save_folder / f"{item_folder.name}_{surface_key}_{i}_{j}_{x}_{y}_{w}_{h}.png"
                        Image.fromarray(clip_image).save(save_name)
            except (OSError, ValueError) as e:
                logger.warning("clip surface image failed: %s error=%s", item_folder, e)


if __name__ == "__main__":
    clip_surface_images()
