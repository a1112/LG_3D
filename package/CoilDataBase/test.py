import logging

from CoilDataBase import config
from CoilDataBase.Coil import get_all_join_query
from CoilDataBase.core import Session

logger = logging.getLogger(__name__)


def log_join_query_sample(limit: int = 10) -> None:
    with Session() as session:
        results = get_all_join_query(session)[:limit]
        for coil in results:
            logger.info("SecondaryCoil: %s", coil.Id)
            logger.info("childrenCoil: %s", coil.childrenCoil)
            logger.info("childrenAlarmFlatRoll: %s", coil.childrenAlarmFlatRoll)
            logger.info("childrenTaperShapePoint: %s", coil.childrenTaperShapePoint)
            logger.info("childrenAlarmInfo: %s", coil.childrenAlarmInfo)
            logger.info("childrenAlarmTaperShape: %s", coil.childrenAlarmTaperShape)
            logger.info("childrenDetectionSpeed: %s", coil.childrenDetectionSpeed)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    from CoilDataBase.backup import backup_to_sqlite

    config.Config.host = "192.168.99.100"
    backup_to_sqlite("test.db")
    log_join_query_sample()
