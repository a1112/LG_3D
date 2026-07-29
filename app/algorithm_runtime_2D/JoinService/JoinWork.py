import os
import time

from .WorkBase import WorkBaseThread
from algorithm_runtime_2D.configs.JoinConfig import JoinConfig
from .SurfaceWork import SurfaceWork
from algorithm_runtime_2D.utils.MultiprocessColorLogger import logger


def _float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default))
    try:
        return max(float(raw_value), 1.0)
    except ValueError:
        logger.warning("invalid %s=%s, use %s", name, raw_value, default)
        return default


def _int_env(name: str, default: int, minimum: int = 0) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return max(int(raw_value), minimum)
    except ValueError:
        logger.warning("invalid %s=%s, use %s", name, raw_value, default)
        return default


SURFACE_RESULT_TIMEOUT = _float_env("ALG_2D_SURFACE_RESULT_TIMEOUT", 180.0)
SOURCE_QUIET_SECONDS = _float_env("ALG_2D_SOURCE_QUIET_SECONDS", 10.0)
MIN_IMAGES_PER_CAMERA = _int_env("ALG_2D_MIN_IMAGES_PER_CAMERA", 2, 1)
MAX_CAMERA_COUNT_SKEW = _int_env("ALG_2D_MAX_CAMERA_COUNT_SKEW", 2)

class JoinWork(WorkBaseThread):
    """
      对于 整体的  拼接  工作
      主要类别
    """
    def __init__(self, config:JoinConfig):
        super().__init__(config, deduplicate=True)
        self.config: JoinConfig
        self.surface_dict = {
            key: SurfaceWork(key, surface_config)
            for key, surface_config in self.config.surfaces.items()
        }
        self._run_ = True
        self.start()

    def pending_coil_ids(self) -> set:
        coil_ids = super().pending_work_ids()
        for surface in tuple(self.surface_dict.values()):
            coil_ids.update(surface.pending_work_ids())
            for camera_work in tuple(getattr(surface, "cameras_wolk", ())):
                coil_ids.update(camera_work.pending_work_ids())
            save_work = getattr(surface, "save_wolk", None)
            if save_work is not None:
                coil_ids.update(save_work.pending_work_ids())
        return coil_ids

    def _child_workers(self):
        return tuple(self.surface_dict.values())

    def has_pending_work(self, coil_id) -> bool:
        return coil_id in self.pending_coil_ids()

    def pending_work_count(self) -> int:
        return len(self.pending_coil_ids())

    def wait_for_all_work(self, coil_id, timeout: float | None = None) -> bool:
        deadline = None if timeout is None else time.monotonic() + timeout
        while self.has_pending_work(coil_id):
            if self._stop_event.is_set():
                return False
            if deadline is not None and time.monotonic() >= deadline:
                return False
            time.sleep(0.05)
        return True

    def run(self):
        while True:
            work_request = self.get_next_work()
            if work_request is None:
                break
            coil_id = self.get_work_value(work_request)
            self.mark_started(work_request)
            try:
                logger.info("2D join received coil_id=%s", coil_id)
                submitted_surfaces = []
                for key, surface in self.surface_dict.items():
                    if surface.config.area_output_complete(coil_id):
                        logger.debug("2D join skipped processed surface: surface=%s coil_id=%s", key, coil_id)
                        continue
                    if not surface.config.source_complete(
                            coil_id,
                            min_images_per_camera=MIN_IMAGES_PER_CAMERA,
                            max_camera_count_skew=MAX_CAMERA_COUNT_SKEW,
                            quiet_seconds=SOURCE_QUIET_SECONDS,
                    ):
                        logger.info(
                            "2D join deferred incomplete or changing surface: surface=%s coil_id=%s",
                            key,
                            coil_id,
                        )
                        continue
                    ticket = surface.add_work(coil_id)
                    if ticket:
                        submitted_surfaces.append((key, surface, ticket))
                    else:
                        logger.warning("2D join skipped busy surface: surface=%s coil_id=%s", key, coil_id)

                deadline = time.monotonic() + SURFACE_RESULT_TIMEOUT
                for key, surface, ticket in submitted_surfaces:
                    remaining = max(deadline - time.monotonic(), 0.0)
                    surface.get(timeout=remaining, expected_ticket=ticket)
                logger.info(
                    "2D join finished coil_id=%s surfaces=%s",
                    coil_id,
                    [key for key, _, _ in submitted_surfaces],
                )
            except Exception as e:
                logger.exception("2D join failed coil_id=%s: %s", coil_id, e)
            finally:
                self.mark_finished(work_request)
                self.queue_in.task_done()
