import logging
import time

from server import read_plc

logger = logging.getLogger(__name__)


def read_measurements():
    distance = read_plc("DB35.340", "int", 4)
    axis1_pos = read_plc("DB32.600", "real", 4)
    axis2_pos = read_plc("DB32.604", "real", 4)
    logger.info(
        "distance(DB35.340)=%s axis1_pos(DB32.600)=%s axis2_pos(DB32.604)=%s",
        distance,
        axis1_pos,
        axis2_pos,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    while True:
        time.sleep(4)
        read_measurements()
