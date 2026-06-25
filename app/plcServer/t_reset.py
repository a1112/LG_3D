import logging
import time

from server import read_plc, write_plc

logger = logging.getLogger(__name__)


def reset() -> None:
    write_plc("M7.0", "bool", True)
    write_plc("M20.0", "bool", True)
    time.sleep(1)
    write_plc("M7.0", "bool", False)
    write_plc("M20.0", "bool", False)


def read_reset() -> None:
    m7d0 = read_plc("M7.0", "bool", 1)
    m8d1 = read_plc("M8.1", "bool", 1)
    logger.info("M7.0=%s M8.1=%s", m7d0, m8d1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    read_reset()
