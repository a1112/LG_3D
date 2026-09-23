import datetime
import os
import time

import logging
from collections import deque
from pathlib import Path
from typing import List, Tuple

import AlarmDetection
import AlarmDetection.detection
from Base.CONFIG import isLoc, serverConfigProperty
from Init import ErrorMap
from Base.property.Base import DataIntegrationList
from Base.utils.Log import logger
from Base.utils.LoggerProcess import LoggerProcess
from CoilDataBase import Coil
from CoilDataBase import tool as coil_data_base_tool
from CoilDataBase.Alarm import Session as CoilSession
from CoilDataBase.models.Coil import Coil as CoilModel
from CoilDataBase.models.SecondaryCoil import SecondaryCoil as SecondaryCoilModel
from Base.alg import detection as cv_detection
from threading import Event, Thread
from .ImageMosaic import ImageMosaic
from algorithm_runtime.runtime_heartbeat import runtime_heartbeat
import Globs

DEFAULT_MAX_HISTORY_COIL_COUNT = 10
DEFAULT_MAX_RE_DETECTION_COIL_COUNT = 500
MAX_RE_DETECTION_MESSAGE_COUNT = 50
DEFAULT_MISSING_OUTPUT_GRACE_SECONDS = 120
DEFAULT_MISSING_OUTPUT_RETRY_SECONDS = 600
DEFAULT_DUPLICATE_SCAN_WARN_SECONDS = 300
DEFAULT_COIL_PROCESSING_TIMEOUT_SECONDS = 60.0
DEFAULT_REPROCESS_MISSING_OUTPUTS = False


def _get_max_history_coil_count() -> int:
    raw_value = os.getenv("ALGORITHM_3D_MAX_HISTORY_COIL_COUNT",
                          str(DEFAULT_MAX_HISTORY_COIL_COUNT))
    try:
        return max(int(raw_value), 1)
    except ValueError:
        logger.warning(
            "invalid ALGORITHM_3D_MAX_HISTORY_COIL_COUNT=%s, use %s",
            raw_value,
            DEFAULT_MAX_HISTORY_COIL_COUNT,
        )
        return DEFAULT_MAX_HISTORY_COIL_COUNT


MAX_HISTORY_COIL_COUNT = _get_max_history_coil_count()


def _get_max_re_detection_coil_count() -> int:
    raw_value = os.getenv("LG3D_MAX_RE_DETECTION_COILS",
                          str(DEFAULT_MAX_RE_DETECTION_COIL_COUNT))
    try:
        return max(int(raw_value), 1)
    except ValueError:
        logger.warning(
            "invalid LG3D_MAX_RE_DETECTION_COILS=%s, use %s",
            raw_value,
            DEFAULT_MAX_RE_DETECTION_COIL_COUNT,
        )
        return DEFAULT_MAX_RE_DETECTION_COIL_COUNT


MAX_RE_DETECTION_COIL_COUNT = _get_max_re_detection_coil_count()


def _get_missing_output_grace_seconds() -> float:
    raw_value = os.getenv("ALGORITHM_3D_MISSING_OUTPUT_GRACE_SECONDS",
                          str(DEFAULT_MISSING_OUTPUT_GRACE_SECONDS))
    try:
        return max(float(raw_value), 0.0)
    except ValueError:
        logger.warning(
            "invalid ALGORITHM_3D_MISSING_OUTPUT_GRACE_SECONDS=%s, use %s",
            raw_value,
            DEFAULT_MISSING_OUTPUT_GRACE_SECONDS,
        )
        return DEFAULT_MISSING_OUTPUT_GRACE_SECONDS


MISSING_OUTPUT_GRACE_SECONDS = _get_missing_output_grace_seconds()


def _get_missing_output_retry_seconds() -> float:
    raw_value = os.getenv("ALGORITHM_3D_MISSING_OUTPUT_RETRY_SECONDS",
                          str(DEFAULT_MISSING_OUTPUT_RETRY_SECONDS))
    try:
        return max(float(raw_value), 0.0)
    except ValueError:
        logger.warning(
            "invalid ALGORITHM_3D_MISSING_OUTPUT_RETRY_SECONDS=%s, use %s",
            raw_value,
            DEFAULT_MISSING_OUTPUT_RETRY_SECONDS,
        )
        return DEFAULT_MISSING_OUTPUT_RETRY_SECONDS


MISSING_OUTPUT_RETRY_SECONDS = _get_missing_output_retry_seconds()


def _get_duplicate_scan_warn_seconds() -> float:
    raw_value = os.getenv("ALGORITHM_3D_DUPLICATE_SCAN_WARN_SECONDS",
                          str(DEFAULT_DUPLICATE_SCAN_WARN_SECONDS))
    try:
        return max(float(raw_value), 0.0)
    except ValueError:
        logger.warning(
            "invalid ALGORITHM_3D_DUPLICATE_SCAN_WARN_SECONDS=%s, use %s",
            raw_value,
            DEFAULT_DUPLICATE_SCAN_WARN_SECONDS,
        )
        return DEFAULT_DUPLICATE_SCAN_WARN_SECONDS


DUPLICATE_SCAN_WARN_SECONDS = _get_duplicate_scan_warn_seconds()


def _get_coil_processing_timeout_seconds() -> float:
    raw_value = os.getenv("LG3D_COIL_PROCESSING_TIMEOUT_SECONDS",
                          str(DEFAULT_COIL_PROCESSING_TIMEOUT_SECONDS))
    try:
        return max(float(raw_value), 1.0)
    except ValueError:
        logger.warning(
            "invalid LG3D_COIL_PROCESSING_TIMEOUT_SECONDS=%s, use %s",
            raw_value,
            DEFAULT_COIL_PROCESSING_TIMEOUT_SECONDS,
        )
        return DEFAULT_COIL_PROCESSING_TIMEOUT_SECONDS


COIL_PROCESSING_TIMEOUT_SECONDS = _get_coil_processing_timeout_seconds()


def _get_reprocess_missing_outputs() -> bool:
    raw_value = os.getenv("ALGORITHM_3D_REPROCESS_MISSING_OUTPUTS",
                          "1" if DEFAULT_REPROCESS_MISSING_OUTPUTS else "0")
    return raw_value.strip().lower() in ("1", "true", "yes", "on")


REPROCESS_MISSING_OUTPUTS = _get_reprocess_missing_outputs()


class ImageMosaicThread(Thread):
    """
    多线程的主循环
    """

    def __init__(self, manager_queue, logger_process: LoggerProcess):
        logger.debug("ImageMosaicThread init")
        super().__init__(name="image-mosaic-coordinator", daemon=True)
        self._stop_event = Event()
        self.managerQueue = manager_queue
        self.loggerProcess = logger_process
        self.listData = []
        self.saveDataBase = True
        self.debugType = False
        self.maxHistoryCoilCount = max(MAX_HISTORY_COIL_COUNT, 1)
        self.imageMosaicList: List[ImageMosaic] = []
        # 重新识别的排队机制（优先级低于新数据）
        self.re_detection_queue: list[int] = []
        self.re_detection_total: int = 0
        self.re_detection_done: int = 0
        self.re_detection_running: bool = False
        self.re_detection_error: str = ""
        self.re_detection_messages = deque(
            maxlen=MAX_RE_DETECTION_MESSAGE_COUNT)
        self._last_missing_output_id_logged: int | None = None
        self._missing_output_retry_after: dict[int, datetime.datetime] = {}
        self._recent_scan_attempts: dict[int, float] = {}

        for surface in serverConfigProperty.surface:
            self.imageMosaicList.append(
                ImageMosaic(surface, self.managerQueue, logger_process))
        try:
            self.startCoilId = Coil.get_coil(1)[0].SecondaryCoilId  # 最新的 数据
            self.endCoilId = Coil.get_secondary_coil(1)[0].Id  # 目标数据
            self.startCoilId = self._limit_history_start_id(
                self.startCoilId, self.endCoilId)
            if REPROCESS_MISSING_OUTPUTS:
                missing_output_cursor = self._find_missing_output_cursor(
                    self.endCoilId)
                if (missing_output_cursor is not None
                        and missing_output_cursor < self.startCoilId):
                    self.startCoilId = missing_output_cursor
        except IndexError:
            logger.error(" ")
            self.startCoilId = 0

    check_num = 0

    def _limit_history_start_id(self, start_coil_id: int,
                                max_secondary_coil_id: int) -> int:
        if self.maxHistoryCoilCount <= 0:
            return max_secondary_coil_id

        min_start_coil_id = max(
            max_secondary_coil_id - self.maxHistoryCoilCount, 0)
        if start_coil_id < min_start_coil_id:
            logger.warning(
                "history data exceeds limit, skip SecondaryCoilId <= %s; "
                "last_processed=%s, latest=%s, max_history=%s",
                min_start_coil_id,
                start_coil_id,
                max_secondary_coil_id,
                self.maxHistoryCoilCount,
            )
            return min_start_coil_id

        return start_coil_id

    @staticmethod
    def _has_nonempty_file(path: Path) -> bool:
        try:
            return path.is_file() and path.stat().st_size > 0
        except OSError:
            return False

    @classmethod
    def _has_any_nonempty_file(cls, paths: Tuple[Path, ...]) -> bool:
        return any(cls._has_nonempty_file(path) for path in paths)

    def _surface_outputs_complete(self, image_mosaic: ImageMosaic,
                                  coil_id: int) -> bool:
        output_dir = image_mosaic.saveFolder / str(coil_id)
        required_files = [
            (output_dir / "3D.npz", output_dir / "3D.npy"),
            (output_dir / "jpg" / "GRAY.jpg", output_dir / "png" / "GRAY.png"),
        ]
        for renderer in getattr(serverConfigProperty, "renderer_list",
                                []) or []:
            required_files.append((
                output_dir / "jpg" / f"{renderer}.jpg",
                output_dir / "png" / f"{renderer}.png",
            ))
        return all(
            self._has_any_nonempty_file(paths) for paths in required_files)

    def _coil_outputs_complete(self, coil_id: int) -> bool:
        return all(
            self._surface_outputs_complete(image_mosaic, coil_id)
            for image_mosaic in self.imageMosaicList)

    def _coil_capture_complete(self, coil_id: int) -> bool:
        return all(
            image_mosaic.check_detection_end(str(coil_id))
            for image_mosaic in self.imageMosaicList)

    def _record_scan_attempt(self, coil_id: int, reason: str) -> None:
        if DUPLICATE_SCAN_WARN_SECONDS <= 0:
            return

        now = time.monotonic()
        previous = self._recent_scan_attempts.get(coil_id)
        if previous is not None:
            age_s = now - previous
            if age_s <= DUPLICATE_SCAN_WARN_SECONDS:
                logger.warning(
                    "duplicate scan attempt detected SecondaryCoilId=%s reason=%s previous_age_s=%.1f",
                    coil_id,
                    reason,
                    age_s,
                )

        self._recent_scan_attempts[coil_id] = now
        cutoff = now - DUPLICATE_SCAN_WARN_SECONDS
        for cached_id, cached_time in list(self._recent_scan_attempts.items()):
            if cached_time < cutoff:
                self._recent_scan_attempts.pop(cached_id, None)

    def _update_missing_output_retry(self, coil_id: int) -> None:
        if (not REPROCESS_MISSING_OUTPUTS
                or MISSING_OUTPUT_RETRY_SECONDS <= 0):
            return

        if self._coil_outputs_complete(coil_id):
            self._missing_output_retry_after.pop(coil_id, None)
            return

        retry_after = datetime.datetime.now() + datetime.timedelta(
            seconds=MISSING_OUTPUT_RETRY_SECONDS)
        self._missing_output_retry_after[coil_id] = retry_after
        logger.warning(
            "3D output still incomplete after scan SecondaryCoilId=%s; suppress missing-output rewind until %s",
            coil_id,
            retry_after.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def _find_missing_output_cursor(self,
                                    max_secondary_coil_id: int) -> int | None:
        if not REPROCESS_MISSING_OUTPUTS:
            return None
        min_secondary_coil_id = max(
            max_secondary_coil_id - self.maxHistoryCoilCount, 0)
        now = datetime.datetime.now()
        grace_cutoff = now - datetime.timedelta(
            seconds=MISSING_OUTPUT_GRACE_SECONDS)

        with CoilSession() as session:
            rows = (session.query(
                CoilModel.SecondaryCoilId, CoilModel.DetectionTime
            ).filter(CoilModel.SecondaryCoilId > min_secondary_coil_id).filter(
                CoilModel.SecondaryCoilId <= max_secondary_coil_id).order_by(
                    CoilModel.SecondaryCoilId.desc()).all())

        missing_start_id = None
        for secondary_coil_id, detection_time in rows:
            secondary_coil_id = int(secondary_coil_id)
            if detection_time is not None and detection_time > grace_cutoff:
                continue
            if not self._coil_capture_complete(secondary_coil_id):
                continue
            retry_after = self._missing_output_retry_after.get(
                secondary_coil_id)
            if retry_after is not None:
                if retry_after > now:
                    continue
                self._missing_output_retry_after.pop(secondary_coil_id, None)
            if self._coil_outputs_complete(secondary_coil_id):
                self._missing_output_retry_after.pop(secondary_coil_id, None)
                if missing_start_id is not None:
                    break
                continue
            missing_start_id = secondary_coil_id

        if missing_start_id is not None:
            if self._last_missing_output_id_logged != missing_start_id:
                logger.warning(
                    "3D output files missing for recent recorded SecondaryCoilId=%s; rewind cursor for reprocessing",
                    missing_start_id,
                )
                self._last_missing_output_id_logged = missing_start_id
            return max(missing_start_id - 1, 0)

        self._last_missing_output_id_logged = None
        return None

    def check_detection_end(self, secondary_coil_id):
        for imageMosaic in self.imageMosaicList:
            if not imageMosaic.check_detection_end(secondary_coil_id):
                self.check_num += 1
                if not (self.check_num % 10):
                    logger.error("checkDetectionEnd %s", secondary_coil_id)
                return False
        return True

    def _process_secondary_coil(
        self,
        secondary_coil: SecondaryCoilModel,
        max_secondary_coil_id: int,
        run_num: int,
        check_detection: bool = True,
    ) -> Tuple[bool, int]:
        """
        处理单个二级卷的完整检测流程。
        """
        defection_time1 = time.time()
        processing_deadline = (time.monotonic() +
                               COIL_PROCESSING_TIMEOUT_SECONDS)
        less_num = max_secondary_coil_id - secondary_coil.Id
        if max_secondary_coil_id - secondary_coil.Id > 2:
            logger.debug("clear old coil data SecondaryCoilId=%s",
                         secondary_coil.Id)
            coil_data_base_tool.clear_by_coil_id(secondary_coil.Id)
        if check_detection and less_num < 1:
            if not self.check_detection_end(secondary_coil.Id):
                # 采集未完成
                return False, run_num

        scan_reason = "online" if check_detection else "manual_or_history"
        self._record_scan_attempt(secondary_coil.Id, scan_reason)
        logger.debug(
            "start processing SecondaryCoilId=%s remaining=%s processed=%s",
            secondary_coil.Id,
            less_num,
            run_num,
        )
        run_num += 1
        self.startCoilId = secondary_coil.Id

        status = {}
        mosaic_error_msgs = []
        for imageMosaic in self.imageMosaicList:  # 设置 ID
            set_ok = imageMosaic.set_coil_id(secondary_coil.Id,
                                             secondary_coil=secondary_coil)
            status[imageMosaic.key] = 0
            if not set_ok:
                logger.error("setOK: %s", set_ok)
                mosaic_error_msgs.append(
                    f"{imageMosaic.key}: set_coil_id failed")
                status[imageMosaic.key] = ErrorMap["DataFolderError"]
                continue

        data_integration_list = DataIntegrationList()
        for imageMosaic in self.imageMosaicList:  # 获取图片
            if status[imageMosaic.key] < 0:
                continue
            try:
                data_integration = imageMosaic.get_data(
                    expected_coil_id=secondary_coil.Id)
            except TimeoutError as e:
                logger.error(
                    "image mosaic result timeout SecondaryCoilId=%s surface=%s: %s",
                    secondary_coil.Id,
                    imageMosaic.key,
                    e,
                )
                status[imageMosaic.key] = ErrorMap["DataFolderError"]
                mosaic_error_msgs.append(f"{imageMosaic.key}: {e}")
                continue
            error_msg = getattr(data_integration, "processing_error", "")
            if error_msg:
                logger.error("image processing failed %s surface=%s error=%s",
                             secondary_coil.Id, imageMosaic.key, error_msg)
                mosaic_error_msgs.append(f"{imageMosaic.key}: {error_msg}")
                status[imageMosaic.key] = ErrorMap["ImageError"]
                continue
            if data_integration.isNone():
                logger.error("image is None %s surface=%s error=%s",
                             secondary_coil.Id, imageMosaic.key, error_msg)
                mosaic_error_msgs.append(
                    f"{imageMosaic.key}: {error_msg or 'image is None'}")
                status[imageMosaic.key] = ErrorMap["ImageError"]
                continue
            data_integration_list.append(data_integration)  # 检测

        defection_time3 = time.time()
        detection_error_msg = "; ".join(mosaic_error_msgs)
        if data_integration_list:
            try:
                surface_errors = cv_detection.detection_all(data_integration_list) or {}
                for surface, error in surface_errors.items():
                    status[surface] = ErrorMap["ImageError"]
                    detection_error_msg = "; ".join(
                        msg for msg in (detection_error_msg,
                                        f"{surface}: cv detection failed: {error}") if msg)
            except Exception as e:
                detection_error_msg = "; ".join(
                    msg for msg in (detection_error_msg,
                                    f"cv detection failed: {e}") if msg)
                logger.exception("cv detection failed SecondaryCoilId=%s",
                                 secondary_coil.Id)
                for data_integration in data_integration_list:
                    status[data_integration.key] = ErrorMap["ImageError"]
        else:
            detection_error_msg = "; ".join(
                msg for msg in (detection_error_msg,
                                "no image mosaic data available") if msg)
            logger.error(
                "no image mosaic data available SecondaryCoilId=%s status=%s",
                secondary_coil.Id, status)
        defection_time4 = time.time()
        alarm_error_msg = ""
        if time.monotonic() >= processing_deadline:
            alarm_error_msg = (
                "alarm detection skipped: coil processing timeout "
                f"{COIL_PROCESSING_TIMEOUT_SECONDS}s")
            logger.error("%s SecondaryCoilId=%s", alarm_error_msg,
                         secondary_coil.Id)
            for data_integration in data_integration_list:
                status[data_integration.key] = ErrorMap["ImageError"]
        else:
            try:
                alarm_errors = AlarmDetection.detection.detection_all(
                    data_integration_list) or {}
                for surface, errors in alarm_errors.items():
                    status[surface] = ErrorMap["ImageError"]
                    detail = "; ".join(errors) if isinstance(errors, (list, tuple)) else str(errors)
                    alarm_error_msg = "; ".join(
                        msg for msg in (alarm_error_msg, f"{surface}: {detail}") if msg)
            except Exception as e:
                alarm_error_msg = f"alarm detection failed: {e}"
                logger.exception("alarm detection failed SecondaryCoilId=%s",
                                 secondary_coil.Id)
                for data_integration in data_integration_list:
                    status[data_integration.key] = ErrorMap["ImageError"]
        defection_time5 = time.time()
        processing_error = "; ".join(
            msg for msg in (detection_error_msg, alarm_error_msg) if msg)
        if processing_error and not check_detection and getattr(self, "re_detection_running", False):
            self.re_detection_error = f"{secondary_coil.Id}: {processing_error}"
            self.add_msg(self.re_detection_error)

        logger.debug(
            "algorithm timing total_s=%s image_s=%s defect_s=%s alarm_s=%s",
            defection_time5 - defection_time1,
            defection_time3 - defection_time1,
            defection_time4 - defection_time3,
            defection_time5 - defection_time4,
        )
        if self.saveDataBase:
            Coil.addCoil({
                "SecondaryCoilId":
                secondary_coil.Id,
                "DefectCountS":
                0,
                "DefectCountL":
                0,
                "CheckStatus":
                0,
                "Status_L":
                status.get("L", 0),
                "Status_S":
                status.get("S", 0),
                "Grade":
                0,
                "Msg":
                processing_error
            })
            # 检测完成后同步摘要表
            try:
                from CoilDataBase.CoilSummary import sync_coil_summary
                with CoilSession() as sync_session:
                    sync_coil_summary(sync_session, secondary_coil.Id)
            except Exception as e:
                logger.error("sync coil summary failed SecondaryCoilId=%s: %s",
                             secondary_coil.Id, e)
        self._update_missing_output_retry(secondary_coil.Id)
        if isLoc:
            sleep_time = Globs.control.loc_sleep_time
            if status.get("L", 0) < 0 and status.get("S", 0) < 0:
                sleep_time = 0.1
            logger.debug("loc model sleep %s", sleep_time)
            time.sleep(sleep_time)
            logger.debug("loc model sleep %s end", sleep_time)

        return True, run_num

    def _process_secondary_coil_supervised(self, *args, **kwargs):
        """Register work so the process watchdog can detect native stalls."""
        secondary_coil = kwargs.get("secondary_coil")
        coil_id = getattr(secondary_coil, "Id", None)
        activity = runtime_heartbeat.begin_activity(
            "3d_coil_processing",
            coil_id,
        )
        try:
            return self._process_secondary_coil(*args, **kwargs)
        finally:
            runtime_heartbeat.end_activity(activity)

    def stop(self) -> None:
        self._stop_event.set()
        for image_mosaic in tuple(self.imageMosaicList):
            try:
                image_mosaic.request_stop()
            except Exception as e:
                logger.exception(
                    "ImageMosaic stop request failed surface=%s: %s",
                    getattr(image_mosaic, "key", None),
                    e,
                )

    def run(self):
        logger.debug("run algorithm main thread")
        while not self._stop_event.is_set():
            run_num = 0
            try:
                max_secondary_coil_id = Coil.get_secondary_coil(1)[0].Id
                self.startCoilId = self._limit_history_start_id(
                    self.startCoilId, max_secondary_coil_id)
                if REPROCESS_MISSING_OUTPUTS:
                    missing_output_cursor = self._find_missing_output_cursor(
                        max_secondary_coil_id)
                    if (missing_output_cursor is not None
                            and missing_output_cursor < self.startCoilId):
                        self.startCoilId = missing_output_cursor
                list_data = Coil.get_secondary_coil_by_id(
                    self.startCoilId,
                    limit=self.maxHistoryCoilCount,
                    desc=False,
                )
                # list_data = list_data[-3:]
                for secondary_coil in list_data:
                    if self._stop_event.is_set():
                        break
                    try:
                        should_continue, run_num = self._process_secondary_coil_supervised(
                            secondary_coil=secondary_coil,
                            max_secondary_coil_id=max_secondary_coil_id,
                            run_num=run_num,
                            check_detection=True,
                        )
                        if not should_continue:
                            break
                    except Exception as e:
                        logger.error("process secondary coil failed: %s", e)
                        if isLoc:
                            raise

                # 在线数据处理完成后，再按队列处理重新识别任务（优先级低于新数据）
                if (not self._stop_event.is_set() and not list_data
                        and self.re_detection_queue):
                    from CoilDataBase.core import Session as InnerSession
                    try:
                        self.re_detection_running = True
                        re_coil_id = self.re_detection_queue.pop(0)
                        logger.info(
                            "re-detection queue processing SecondaryCoilId=%s",
                            re_coil_id)
                        with InnerSession() as session:
                            secondary_coil = (
                                session.query(SecondaryCoilModel).filter(
                                    SecondaryCoilModel.Id ==
                                    re_coil_id).first())
                        if secondary_coil is not None:
                            _, _ = self._process_secondary_coil_supervised(
                                secondary_coil=secondary_coil,
                                max_secondary_coil_id=max_secondary_coil_id,
                                run_num=0,
                                check_detection=False,
                            )
                        else:
                            logger.warning(
                                "re-detection queue SecondaryCoilId=%s not found, skip",
                                re_coil_id)
                        self.re_detection_done += 1
                    except Exception as e:
                        logger.error(
                            "re-detection queue failed SecondaryCoilId=%s: %s",
                            re_coil_id, e)
                        self.re_detection_error = str(e)
                        if isLoc:
                            raise
                    finally:
                        if not self.re_detection_queue:
                            self.re_detection_running = False

            except Exception:
                logger.exception("ImageMosaicThread loop failed")
                if isLoc:
                    raise
            finally:
                import torch
                torch.cuda.empty_cache()
            self._stop_event.wait(1)

    def run_missing_coils_by_diff(self,
                                  start_id: int | None = None,
                                  end_id: int | None = None) -> None:
        """
        根据 SecondaryCoil / Coil 差异重新运行缺失历史数据。

        从大到小遍历 SecondaryCoil 表，对于 Coil 中不存在对应 SecondaryCoilId 的记录，
        复用在线检测的逻辑重新执行一次检测。

        Args:
            start_id: 起始 SecondaryCoil.Id（包含），为空则从最大 Id 开始。
            end_id: 结束 SecondaryCoil.Id（包含），为空则遍历到最小 Id。
        """
        logger.debug("开始根据数据库差异重算历史数据")
        import torch

        with CoilSession() as session:
            query = session.query(SecondaryCoilModel)
            if start_id is not None:
                query = query.filter(SecondaryCoilModel.Id >= start_id)
            if end_id is not None:
                query = query.filter(SecondaryCoilModel.Id <= end_id)
            query = query.order_by(SecondaryCoilModel.Id.desc())

            last_secondary = session.query(SecondaryCoilModel).order_by(
                SecondaryCoilModel.Id.desc()).first()
            if not last_secondary:
                logger.warning("SecondaryCoil 表为空, 无需重算")
                return
            max_secondary_coil_id = last_secondary.Id

            run_num = 0
            for secondary_coil in query:
                exists = (session.query(CoilModel).filter(
                    CoilModel.SecondaryCoilId == secondary_coil.Id).first())
                if exists and self._coil_outputs_complete(secondary_coil.Id):
                    continue
                if exists:
                    logger.warning(
                        "history recompute SecondaryCoilId=%s because 3D output files are missing",
                        secondary_coil.Id,
                    )

                logger.info("history recompute SecondaryCoilId=%s",
                            secondary_coil.Id)
                try:
                    should_continue, run_num = self._process_secondary_coil_supervised(
                        secondary_coil=secondary_coil,
                        max_secondary_coil_id=max_secondary_coil_id,
                        run_num=run_num,
                        check_detection=False,
                    )
                    torch.cuda.empty_cache()
                    if not should_continue:
                        # 历史模式下通常不依赖采集结束状态，这里仅预留扩展
                        break
                except Exception as e:
                    logger.error(
                        "history recompute SecondaryCoilId=%s failed: %s",
                        secondary_coil.Id, e)
                    if isLoc:
                        raise

        logger.debug("历史数据重算完成")

    def add_msg(self, msg, level=logging.DEBUG):
        self.re_detection_messages.append({
            "Base":
            "ImageMosaicThread",
            "time":
            datetime.datetime.now().strftime(Globs.control.exportTimeFormat),
            "msg":
            msg,
            "level":
            logging.getLevelName(level),
        })

    def set_re_detection_by_coil_id(self, startId, endId):
        """
        设置重新识别的 coilId 队列（从大到小），用于历史数据补算。
        """
        start_id = int(startId)
        end_id = int(endId)
        if end_id < start_id:
            start_id, end_id = end_id, start_id
        ids = Coil.get_secondary_coil_ids_by_range(
            start_id,
            end_id,
            max_count=MAX_RE_DETECTION_COIL_COUNT,
        )
        self.re_detection_queue = ids
        self.re_detection_total = len(ids)
        self.re_detection_done = 0
        self.re_detection_running = False
        self.re_detection_error = ""
        self.add_msg(
            f"set_re_detection_by_coil_id start={start_id} end={end_id} count={len(ids)}"
        )

    def set_re_detection(self, coilId):
        # 设置单个重新检测 列表项
        coil_id = int(getattr(coilId, "Id", coilId))
        if coil_id not in self.re_detection_queue:
            if len(self.re_detection_queue) >= MAX_RE_DETECTION_COIL_COUNT:
                raise ValueError(
                    "re-detection queue exceeds "
                    f"{MAX_RE_DETECTION_COIL_COUNT} coils")
            self.re_detection_queue.append(coil_id)
            self.re_detection_total += 1
            self.add_msg(f"set_re_detection {coil_id}")

    def get_re_detection_msg(self):
        """
        获取重新识别任务状态，用于前端进度显示。
        """
        total = self.re_detection_total
        done = self.re_detection_done
        pending = max(total - done, 0)
        progress = 0.0
        if total > 0:
            progress = done / total
        queue_size = len(self.re_detection_queue)
        queue_preview = list(
            self.re_detection_queue[:MAX_RE_DETECTION_COIL_COUNT])
        return {
            "total": total,
            "done": done,
            "pending": pending,
            "running": self.re_detection_running,
            "error": self.re_detection_error,
            "queue": queue_preview,
            "queue_size": queue_size,
            "queue_truncated": queue_size > len(queue_preview),
            "messages": list(self.re_detection_messages),
            "progress": progress,
        }
