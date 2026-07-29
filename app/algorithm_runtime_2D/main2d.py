import os
import sys
import time
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from Base.utils.watchdog_bootstrap import maybe_exec_watchdog

maybe_exec_watchdog(
    __name__,
    Path(__file__).with_name("watchdog.py"),
    child_environment="LG3D_ALGORITHM_2D_WATCHDOG_CHILD",
    disable_environment="LG3D_ALGORITHM_2D_DISABLE_AUTO_WATCHDOG",
    service_name="LG3D 2D algorithm",
)

from algorithm_runtime_2D.runtime_heartbeat import runtime_heartbeat
from Base.utils.Singleton import SingletonLock
from algorithm_runtime_2D.JoinService.JoinWork import JoinWork
from algorithm_runtime_2D.configs import CONFIG
from algorithm_runtime_2D.configs.JoinConfig import JoinConfig
from algorithm_runtime_2D.utils.MultiprocessColorLogger import logger


DEFAULT_MAX_HISTORY_COIL_COUNT = 500
LOG_INTERVAL = 300
JOIN_RESULT_TIMEOUT = 300
SOURCE_QUIET_SECONDS = 10.0


def _get_max_history_coil_count() -> int:
    raw_value = os.getenv("ALGORITHM_2D_MAX_HISTORY_COIL_COUNT", str(DEFAULT_MAX_HISTORY_COIL_COUNT))
    try:
        return min(max(int(raw_value), 1), 500)
    except ValueError:
        logger.warning(
            "invalid ALGORITHM_2D_MAX_HISTORY_COIL_COUNT=%s, use %s",
            raw_value,
            DEFAULT_MAX_HISTORY_COIL_COUNT,
        )
        return DEFAULT_MAX_HISTORY_COIL_COUNT


MAX_HISTORY_COIL_COUNT = _get_max_history_coil_count()


def _iter_recovery_coils(latest_coil: int):
    min_coil = max(latest_coil - MAX_HISTORY_COIL_COUNT + 1, 0)
    return range(latest_coil, min_coil - 1, -1)


def _surface_source_complete(surface_config, coil_id: int) -> bool:
    return surface_config.source_complete(
        coil_id,
        min_images_per_camera=2,
        max_camera_count_skew=2,
        quiet_seconds=SOURCE_QUIET_SECONDS,
    )


def _coil_needs_work(join_config: JoinConfig, coil_id: int) -> bool:
    for surface in join_config.surfaces.values():
        if surface.area_output_complete(coil_id):
            continue
        if _surface_source_complete(surface, coil_id):
            return True
    return False


def main():
    runtime_lock = SingletonLock("algorithm_runtime_2d")
    if not runtime_lock.acquire():
        raise SystemExit("2D algorithm runtime is already running")
    runtime_heartbeat.start()
    jw = None
    try:
        startup_activity = runtime_heartbeat.begin_activity(
            "2d_runtime_initialization"
        )
        try:
            join_config = JoinConfig(CONFIG.JOIN_CONFIG_FILE)
            jw = JoinWork(join_config)
        finally:
            runtime_heartbeat.end_activity(startup_activity)

        logger.info("2D algorithm recovery newest-first max_history=%s", MAX_HISTORY_COIL_COUNT)

        last_log_time = 0
        while True:
            recovery_coils = join_config.get_source_coil_ids(MAX_HISTORY_COIL_COUNT)
            latest_coil = recovery_coils[0] if recovery_coils else 0
            processed_one = False
            for coil_id in recovery_coils:
                if not _coil_needs_work(join_config, coil_id):
                    continue
                if not join_config.can_(coil_id):
                    continue
                logger.info("2D algorithm processing coil_id=%s latest=%s", coil_id, latest_coil)
                ticket = jw.add_work(coil_id)
                if ticket:
                    if jw.wait_for_all_work(coil_id, timeout=JOIN_RESULT_TIMEOUT):
                        logger.info("2D algorithm finished coil_id=%s", coil_id)
                    else:
                        logger.warning("2D algorithm timed out coil_id=%s", coil_id)
                processed_one = True
                break

            if not processed_one:
                time.sleep(5)
                current_time = time.time()
                if current_time - last_log_time >= LOG_INTERVAL:
                    logger.info("2D algorithm waiting: latest=%s max_history=%s", latest_coil, MAX_HISTORY_COIL_COUNT)
                    last_log_time = current_time
    finally:
        if jw is not None:
            jw.stop(timeout=10)
        runtime_heartbeat.stop()
        runtime_lock.release()


if __name__ == "__main__":
    main()
