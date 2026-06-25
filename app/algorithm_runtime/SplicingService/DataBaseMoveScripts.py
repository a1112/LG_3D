import logging

from CoilDataBase.Alarm import Session
from CoilDataBase.models.SecondaryCoil import SecondaryCoil

logger = logging.getLogger(__name__)


def log_first_secondary_coil() -> None:
    with Session() as session:
        coil = session.query(SecondaryCoil).first()
        logger.info("first SecondaryCoil Id: %s", None if coil is None else coil.Id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    log_first_secondary_coil()
