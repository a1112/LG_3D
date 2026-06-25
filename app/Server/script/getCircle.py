import logging
from pathlib import Path

import cv2
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


def inspect_inner_circle(mask_path: Path) -> None:
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise FileNotFoundError(str(mask_path))
    mask = cv2.bitwise_not(mask)
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) <= 2:
        raise ValueError(f"not enough contours in {mask_path}: {len(contours)}")

    inner_circle_contour = contours[2]
    (x, y), radius = cv2.minEnclosingCircle(inner_circle_contour)

    output_image = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    cv2.circle(output_image, (int(x), int(y)), int(radius), (255, 0, 0), 5)

    ellipse = cv2.fitEllipse(inner_circle_contour)
    cv2.ellipse(output_image, ellipse, (255, 0, 0), 5)

    _, axes, _ = ellipse
    major_axis, minor_axis = axes
    compression_ratio = minor_axis / major_axis if major_axis else 0

    logger.info("circle center=(%s, %s) radius=%s", x, y, radius)
    logger.info("ellipse=%s", ellipse)
    logger.info("ellipse major_axis=%s minor_axis=%s compression_ratio=%.4f",
                major_axis, minor_axis, compression_ratio)

    plt.imshow(output_image)
    plt.show()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    inspect_inner_circle(Path("F:/datasets/LG_3D_DataBase/DataSave/surface_L/1700/MASK.png"))
