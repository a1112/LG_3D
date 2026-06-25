import logging
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def move_mosaic_data(mosaic: Any, save_folder: Path = Path("I:/database/2D")) -> None:
    save_folder.mkdir(exist_ok=True)
    for folder in [Path(mosaic.saveFolder), Path(mosaic.saveFolder)]:
        for item_folder in folder.iterdir():
            logger.debug("move mosaic item folder: %s", item_folder)
            try:
                gray_image = Image.open(item_folder / "GRAY.png")
                mask_image = Image.open(item_folder / "MASK.png")
                gray_image = np.asarray(gray_image)
                mask_image = np.asarray(mask_image)
                n = 10
                h_item_size = mask_image.shape[0] // n
                w_item_size = mask_image.shape[1] // n
                coil_name = item_folder.name
                for i in range(n):
                    for j in range(n):
                        x, y, w, h = w_item_size * j, h_item_size * i, w_item_size, h_item_size
                        clip_image = gray_image[h_item_size * i:h_item_size * (i + 1),
                                                w_item_size * j:w_item_size * (j + 1)]
                        clip_mask = mask_image[h_item_size * i:h_item_size * (i + 1),
                                               w_item_size * j:w_item_size * (j + 1)]
                        if np.count_nonzero(clip_mask) / (clip_mask.shape[0] * clip_mask.shape[1]) > 0.3:
                            save_name = save_folder / f"{coil_name}_{mosaic.key}_{i}_{j}_{x}_{y}_{w}_{h}.png"
                            Image.fromarray(clip_image).save(save_name)
            except FileNotFoundError:
                logger.debug("skip incomplete mosaic item folder: %s", item_folder)
