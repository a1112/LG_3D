import os
import time

from JoinService.JoinWork import JoinWork
from configs import CONFIG
from configs.JoinConfig import JoinConfig
from utils.MultiprocessColorLogger import logger


DEFAULT_MAX_HISTORY_COIL_COUNT = 200
LOG_INTERVAL = 300


def _get_max_history_coil_count() -> int:
    raw_value = os.getenv("ALGORITHM_2D_MAX_HISTORY_COIL_COUNT", str(DEFAULT_MAX_HISTORY_COIL_COUNT))
    try:
        return max(int(raw_value), 1)
    except ValueError:
        logger.warning(
            "invalid ALGORITHM_2D_MAX_HISTORY_COIL_COUNT=%s, use %s",
            raw_value,
            DEFAULT_MAX_HISTORY_COIL_COUNT,
        )
        return DEFAULT_MAX_HISTORY_COIL_COUNT


MAX_HISTORY_COIL_COUNT = _get_max_history_coil_count()


def _limit_history_start_coil(start_coil: int, max_coil: int) -> int:
    min_start_coil = max(max_coil - MAX_HISTORY_COIL_COUNT, 0)
    if start_coil < min_start_coil:
        logger.info(
            "history data exceeds limit, skip coil_id <= %s; last_processed=%s latest=%s max_history=%s",
            min_start_coil,
            start_coil,
            max_coil,
            MAX_HISTORY_COIL_COUNT,
        )
        return min_start_coil

    return start_coil


def main():
    join_config = JoinConfig(CONFIG.JOIN_CONFIG_FILE)
    jw = JoinWork(join_config)

    start_coil = int(join_config.get_last_coil())
    logger.info("2D algorithm start from coil_id=%s", start_coil)
    max_coil = join_config.get_save_max_coil()
    start_coil = _limit_history_start_coil(start_coil, max_coil)

    last_log_time = 0
    while True:
        max_coil = join_config.get_save_max_coil()
        start_coil = _limit_history_start_coil(start_coil, max_coil)
        can_run = join_config.can_(start_coil)
        if not can_run and start_coil >= (max_coil - 2):
            time.sleep(5)
            max_coil = join_config.get_save_max_coil()
            current_time = time.time()
            if current_time - last_log_time >= LOG_INTERVAL:
                logger.info("2D algorithm waiting: start_coil=%s max_coil=%s", start_coil, max_coil)
                last_log_time = current_time
            continue

        start_coil += 1
        logger.info("2D algorithm processing coil_id=%s", start_coil)
        jw.add_work(start_coil)
        jw.get()
        logger.info("2D algorithm finished coil_id=%s", start_coil)


if __name__ == "__main__":
    main()
