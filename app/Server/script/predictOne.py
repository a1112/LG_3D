import logging
from pathlib import Path

from Base.alg.CoilMaskModel import CoilDetectionModel

logger = logging.getLogger(__name__)


def predict_one(image_path: Path) -> None:
    cdm = CoilDetectionModel(base_name="yolo26best.pt")
    result = cdm.predict(str(image_path))
    logger.info("prediction result: %s", result)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    predict_one(Path("E:/train/train/Dataset/images/train/35550_S_4540_4500_590_585.png"))
