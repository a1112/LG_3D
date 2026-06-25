import io
import logging

import numpy as np
from PIL import Image
from skimage.draw import line
from skimage.segmentation import find_boundaries

from tools.DataGet import DataGet

logger = logging.getLogger(__name__)


def extract_segment_values(npy_data, mask_image, p1, p2):
    rr, cc = line(p1[0], p1[1], p2[0], p2[1])
    boundaries = find_boundaries(mask_image, mode="inner")

    intersection_indices = np.where(boundaries[rr, cc])[0]
    if len(intersection_indices) < 2:
        logger.warning("No sufficient intersection points found on the boundary.")
        return []

    intersection_rr = rr[intersection_indices]
    intersection_cc = cc[intersection_indices]
    lines = []
    for i in range(0, len(intersection_rr) - 1, 2):
        pl = (intersection_rr[i], intersection_cc[i])
        pr = (intersection_rr[i + 1], intersection_cc[i + 1])
        segment_rr, segment_cc = line(pl[0], pl[1], pr[0], pr[1])
        segment_values = npy_data[segment_rr, segment_cc]
        segment_points = list(zip(segment_rr, segment_cc, segment_values))
        lines.append(segment_points)

    return lines


def run_sample() -> None:
    data_get = DataGet("image", "L", "1810", "MASK", False)
    jpg_bytes = data_get.get_image()
    mask_image = Image.open(io.BytesIO(jpg_bytes))
    npy_data = data_get.get_3d_data()

    mask_image = np.array(mask_image)
    h, w = mask_image.shape
    p1 = (0, 0)
    p2 = (h - 1, w - 1)
    extract_segment_values(npy_data, mask_image, p1, p2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    run_sample()
