import logging

from Coil import get_coil

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger.info("%s", get_coil(10))
