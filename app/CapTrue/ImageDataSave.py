import json
import os
import time
import uuid
from collections import OrderedDict, deque
from pathlib import Path
from queue import Full, Queue
from threading import Lock, Thread

from PIL import Image

from CONFIG import capTureConfig
from CoilDataBase.Coil import add_obj
from CoilDataBase.models.SecondaryCoil import SecondaryCoil
from CoilDataBase.models.CapTrueLogItem import CapTrueLogItem
from CoilDataBase.storage_policy import should_store_capture_raw_files
from Base.tools.compressed_storage import save_compressed_image, save_compressed_numpy
from ImageBuffer import SickBuffer, DaHengBuffer
from Camera import SickCamera
from Log import logger

CAPTURE_SAVE_QUEUE_PUT_TIMEOUT = float(
    os.getenv("LG3D_CAPTURE_SAVE_QUEUE_PUT_TIMEOUT", "2.0"))
CAPTURE_SAVE_STOP_TIMEOUT = float(
    os.getenv("LG3D_CAPTURE_SAVE_STOP_TIMEOUT", "30.0"))
CAPTURE_SAVE_JOIN_TIMEOUT = float(
    os.getenv("LG3D_CAPTURE_SAVE_JOIN_TIMEOUT", "120.0"))
CAPTURE_MAX_SAVE_INDEX = int(os.getenv("LG3D_CAPTURE_MAX_SAVE_INDEX", "20"))
# A value of 0 disables the byte budget. The per-camera queue still has a hard
# 30-item bound, so a complete capture sequence can be buffered without making
# memory growth unbounded.
DEFAULT_CAPTURE_SAVE_QUEUE_MAX_BYTES = 0
CAPTURE_SAVE_QUEUE_MAX_BYTES = max(
    0,
    int(
        os.getenv(
            "LG3D_CAPTURE_SAVE_QUEUE_MAX_BYTES",
            str(DEFAULT_CAPTURE_SAVE_QUEUE_MAX_BYTES),
        )),
)
CAPTURE_SAVE_STALL_SECONDS = max(
    1.0, float(os.getenv("LG3D_CAPTURE_SAVE_STALL_SECONDS", "120.0")))
CAPTURE_SAVE_DROP_LOG_INTERVAL = max(
    1.0, float(os.getenv("LG3D_CAPTURE_SAVE_DROP_LOG_INTERVAL", "10.0")))
CAPTURE_SAVE_INDEX_LOG_INTERVAL = max(
    1.0, float(os.getenv("LG3D_CAPTURE_SAVE_INDEX_LOG_INTERVAL", "60.0")))
CAPTURE_INDEX_CACHE_SIZE = max(
    1, int(os.getenv("LG3D_CAPTURE_INDEX_CACHE_SIZE", "1000")))


class ImageDataSave(Thread):

    def __init__(self, save_folder):
        super().__init__()
        self.saveFolder = Path(save_folder)
        self.name = self.saveFolder.name
        self.save_index = 0
        self.save_index_2d = 0
        self.active_coil_id = None
        self.index_lock = Lock()
        self.capture_index_high_water = OrderedDict()
        self.queue = Queue(maxsize=30)
        self.running = True
        self.stop_lock = Lock()
        self.stop_signal_enqueued = False
        self.daemon = True
        self.camera: SickCamera | None = None
        self.created_files = deque(maxlen=200)
        self.dropped_buffers = 0
        self.queued_bytes = 0
        self.queue_memory_lock = Lock()
        self.operation_lock = Lock()
        self.operation_name = ""
        self.operation_started_at = 0.0
        self.operation_started_monotonic = 0.0
        self.last_saved_at = 0.0
        self.last_save_error = ""
        self.last_drop_log_time = 0.0
        self.last_index_log_time = 0.0
        self.start()

    def set_camera(self, camera):
        self.camera = camera

    @staticmethod
    def _write_json_atomic(data, save_file):
        save_file = Path(save_file)
        save_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = save_file.with_name(
            f".{save_file.stem}.{uuid.uuid4().hex}.tmp{save_file.suffix}")
        try:
            with temporary.open("w", encoding="utf-8") as f:
                json.dump(data,
                          f,
                          indent=4,
                          ensure_ascii=False,
                          sort_keys=True)
            os.replace(temporary, save_file)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _coil_id(coil):
        return str(getattr(coil, "Id", coil))

    def _next_saved_index(self, coil_id, folder_names):
        indices = []
        for folder_name in folder_names:
            folder = self.saveFolder / coil_id / folder_name
            if not folder.exists():
                continue
            for path in folder.iterdir():
                if not path.is_file():
                    continue
                try:
                    indices.append(int(path.stem))
                except ValueError:
                    continue
        return max(indices, default=-1) + 1

    def _store_high_water(self, coil_id, value):
        self.capture_index_high_water[coil_id] = value
        self.capture_index_high_water.move_to_end(coil_id)
        while len(self.capture_index_high_water) > CAPTURE_INDEX_CACHE_SIZE:
            self.capture_index_high_water.popitem(last=False)

    def _resume_capture_indices(self, coil):
        coil_id = self._coil_id(coil)
        with self.index_lock:
            saved_3d_index = self._next_saved_index(
                coil_id, ("2d", "2D", "3d", "3D", "json"))
            saved_2d_index = self._next_saved_index(coil_id, ("area", ))
            high_water = self.capture_index_high_water.get(coil_id, (0, 0))
            self.save_index = max(high_water[0], saved_3d_index)
            self.save_index_2d = max(high_water[1], saved_2d_index)
            self._store_high_water(coil_id, (
                self.save_index,
                self.save_index_2d,
            ))
            self.active_coil_id = coil_id
            return self.save_index, self.save_index_2d

    def _reserve_capture_index(self, coil_id, area=False):
        coil_id = self._coil_id(coil_id)
        with self.index_lock:
            high_water = self.capture_index_high_water.get(coil_id)
            if high_water is None:
                high_water = (
                    self._next_saved_index(coil_id,
                                           ("2d", "2D", "3d", "3D", "json")),
                    self._next_saved_index(coil_id, ("area", )),
                )

            next_3d, next_2d = high_water
            if area:
                save_index = next_2d
                next_2d += 1
            else:
                save_index = next_3d
                next_3d += 1
            self._store_high_water(coil_id, (next_3d, next_2d))

            if coil_id == self.active_coil_id:
                self.save_index = next_3d
                self.save_index_2d = next_2d
            return save_index

    def trigger_init(self, coil: SecondaryCoil):
        logger.debug("triggerInit %s", coil)
        self._resume_capture_indices(coil)

    def trigger_in(self, coil):
        logger.debug("triggerIn %s", coil)
        save_index, save_index_2d = self._resume_capture_indices(coil)
        if save_index > 0 or save_index_2d > 0:
            logger.warning(
                "resume capture without overwriting existing frames: camera=%s coil_id=%s next_3d=%s next_2d=%s",
                self.name,
                self._coil_id(coil),
                save_index,
                save_index_2d,
            )

    def trigger_out(self, coil):
        logger.debug("triggerOut %s", coil)

    def stop(self, timeout=CAPTURE_SAVE_STOP_TIMEOUT):
        deadline = time.monotonic() + max(0.0, timeout)
        with self.stop_lock:
            self.running = False
            if self.stop_signal_enqueued:
                return True

            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    logger.error(
                        "capture save stop signal timed out: camera=%s queue_size=%s",
                        self.name,
                        self._queue_size(),
                    )
                    return False
                try:
                    self.queue.put(None, timeout=min(0.2, remaining))
                    self.stop_signal_enqueued = True
                    return True
                except Full:
                    logger.debug(
                        "capture save queue full while stopping, wait for drain: camera=%s queue_size=%s",
                        self.name,
                        self._queue_size(),
                    )

    def _queue_size(self):
        try:
            return self.queue.qsize()
        except NotImplementedError:
            return None

    @staticmethod
    def _buffer_nbytes(buffer):
        total = 0
        seen = set()
        for name in ("data3D", "data2D"):
            value = getattr(buffer, name, None)
            value_id = id(value)
            if value is None or value_id in seen:
                continue
            seen.add(value_id)
            try:
                total += max(int(value.nbytes), 0)
            except (AttributeError, TypeError, ValueError):
                continue
        return total

    def _reserve_queue_memory(self, buffer):
        buffer_bytes = self._buffer_nbytes(buffer)
        with self.queue_memory_lock:
            if (CAPTURE_SAVE_QUEUE_MAX_BYTES > 0 and buffer_bytes > 0
                    and self.queued_bytes > 0
                    and self.queued_bytes + buffer_bytes
                    > CAPTURE_SAVE_QUEUE_MAX_BYTES):
                return None
            self.queued_bytes += buffer_bytes
        return buffer_bytes

    def _release_queue_memory(self, buffer_bytes):
        with self.queue_memory_lock:
            self.queued_bytes = max(self.queued_bytes - buffer_bytes, 0)

    def _log_drop(self, reason, buffer):
        now = time.monotonic()
        if now - self.last_drop_log_time < CAPTURE_SAVE_DROP_LOG_INTERVAL:
            return
        self.last_drop_log_time = now
        logger.error(
            "capture save buffer dropped: reason=%s camera=%s coil_id=%s index=%s "
            "type=%s dropped=%s queue_size=%s queued_mb=%.1f",
            reason,
            self.name,
            getattr(buffer, "coilId", ""),
            getattr(buffer, "save_index", ""),
            type(buffer).__name__,
            self.dropped_buffers,
            self._queue_size(),
            self.queued_bytes / 1024**2,
        )

    def _queue_buffer(self, buffer) -> bool:
        with self.stop_lock:
            if not self.running:
                self.dropped_buffers += 1
                self._log_drop("worker_stopping", buffer)
                return False
            buffer_bytes = self._reserve_queue_memory(buffer)
            if buffer_bytes is None:
                self.dropped_buffers += 1
                self._log_drop("memory_limit", buffer)
                return False
            try:
                self.queue.put(buffer, timeout=CAPTURE_SAVE_QUEUE_PUT_TIMEOUT)
                return True
            except Full:
                self._release_queue_memory(buffer_bytes)
                self.dropped_buffers += 1
                self._log_drop("queue_full", buffer)
                return False

    def put(self, buffer: SickBuffer | DaHengBuffer):
        if isinstance(buffer, SickBuffer):
            buffer.save_index = self._reserve_capture_index(buffer.coilId)
            if buffer.save_index < CAPTURE_MAX_SAVE_INDEX:
                return self._queue_buffer(buffer)
            else:
                self.dropped_buffers += 1
                self._log_index_limit(buffer)
                return False
        elif isinstance(buffer, DaHengBuffer):
            buffer.save_index = self._reserve_capture_index(buffer.coilId,
                                                            area=True)
            if buffer.save_index < CAPTURE_MAX_SAVE_INDEX:
                return self._queue_buffer(buffer)
            else:
                self.dropped_buffers += 1
                self._log_index_limit(buffer)
                return False
        return False

    def _log_index_limit(self, buffer):
        now = time.monotonic()
        if now - self.last_index_log_time < CAPTURE_SAVE_INDEX_LOG_INTERVAL:
            return
        self.last_index_log_time = now
        logger.info(
            "capture save limit reached: camera=%s coil_id=%s index=%s max=%s type=%s",
            self.name,
            getattr(buffer, "coilId", ""),
            getattr(buffer, "save_index", ""),
            CAPTURE_MAX_SAVE_INDEX,
            type(buffer).__name__,
        )

    def save_camera_config(self, buffer):
        saveFile = self.saveFolder / buffer.coilId / "camera_config.json"
        self._write_json_atomic(self.camera.globCameraInfo, saveFile)
        self._record_created_file(saveFile, "camera_config", buffer)

    def _record_created_file(self, save_file, file_type, buffer):
        self.created_files.append({
            "path":
            str(save_file),
            "type":
            file_type,
            "coilId":
            str(getattr(buffer, "coilId", "")),
            "index":
            int(getattr(buffer, "save_index", 0)),
            "cameraName":
            self.name,
        })

    def get_created_files(self, clear=False):
        files = list(self.created_files)
        if clear:
            self.created_files.clear()
        return files

    def save_json(self, buffer):
        if not should_store_capture_raw_files():
            return
        buffer: SickBuffer
        buffer.data2D_mean = float(buffer.data2D.mean())
        buffer.data3D_mean = float(buffer.data3D.mean())
        save_file = self.saveFolder / buffer.coilId / "json" / f"{buffer.save_index}.json"
        self._write_json_atomic(buffer.get_json(), save_file)
        self._record_created_file(save_file, "json", buffer)

    def save3_d(self, buffer):
        if not should_store_capture_raw_files():
            return
        buffer: SickBuffer
        save_file = self.saveFolder / buffer.coilId / "3d" / f"{buffer.save_index}.npz"
        save_compressed_numpy(buffer.data3D, save_file)
        self._record_created_file(save_file, "3d", buffer)

    def _save_array_image(self, image_array, save_file, file_type, buffer):
        image = Image.fromarray(image_array)
        try:
            save_compressed_image(image, save_file)
        finally:
            image.close()
        self._record_created_file(save_file, file_type, buffer)

    def save_area_2d(self, buffer):
        buffer: DaHengBuffer
        if buffer.if_save_index():
            save_file = self.saveFolder / buffer.coilId / "area" / f"{buffer.save_index}.jpg"
            self._save_array_image(buffer.data2D, save_file, "area", buffer)

    def save2_d(self, buffer):
        save_file = self.saveFolder / buffer.coilId / "2d" / f"{buffer.save_index}.jpg"
        self._save_array_image(buffer.data2D, save_file, "2d", buffer)

    def save_area_2d_(self, buffer):
        if buffer.area_cap is not None:
            save_file = self.saveFolder / buffer.coilId / "2d" / f"{buffer.save_index}.jpg"
            self._save_array_image(buffer.area_cap, save_file, "2d_area",
                                   buffer)

    def save_database(self, buffer):
        if getattr(buffer, "coilData", None) is None:
            logger.debug(
                "skip capture database log without coil object: camera=%s coil_id=%s index=%s",
                self.name,
                buffer.coilId,
                buffer.save_index,
            )
            return None
        try:
            add_obj(
                CapTrueLogItem(secondaryCoilId=buffer.coilId,
                               cameraId=capTureConfig.index(self.name),
                               cameraName=self.name,
                               imageIndex=buffer.save_index))
            return True
        except Exception as e:
            logger.exception(
                "save capture database log failed: camera=%s coil_id=%s index=%s error=%s",
                self.name,
                buffer.coilId,
                buffer.save_index,
                e,
            )
            return False

    def save(self, buffer):
        errors = []
        if isinstance(buffer, SickBuffer):
            buffer: SickBuffer
            try:
                self.save_json(buffer)
            except Exception as e:
                errors.append(f"json: {e}")
                logger.exception(
                    "save capture json failed: camera=%s coil_id=%s index=%s error=%s",
                    self.name, buffer.coilId, buffer.save_index, e)
            try:
                self.save3_d(buffer)
            except Exception as e:
                errors.append(f"3d: {e}")
                logger.exception(
                    "save 3D data failed: camera=%s coil_id=%s index=%s error=%s",
                    self.name, buffer.coilId, buffer.save_index, e)
            try:
                self.save2_d(buffer)
            except Exception as e:
                errors.append(f"2d: {e}")
                logger.exception(
                    "save 2D image failed: camera=%s coil_id=%s index=%s error=%s",
                    self.name, buffer.coilId, buffer.save_index, e)
            if buffer.save_index == 0:
                if self.camera:
                    try:
                        self.save_camera_config(buffer)
                    except Exception as e:
                        errors.append(f"camera_config: {e}")
                        logger.exception(
                            "save camera config failed: camera=%s coil_id=%s error=%s",
                            self.name, buffer.coilId, e)
            # Persist camera data before the database audit row. A database
            # outage must not prevent the irreplaceable raw frame from reaching
            # disk; a stalled DB call is then visible through saveWorker status.
            if self.save_database(buffer) is False:
                errors.append("database audit row failed")
        if isinstance(buffer, DaHengBuffer):
            buffer: DaHengBuffer
            try:
                self.save_area_2d(buffer)
            except Exception as e:
                errors.append(f"area: {e}")
                logger.exception(
                    "save 2D AREA image failed: camera=%s coil_id=%s index=%s error=%s",
                    self.name, buffer.coilId, buffer.save_index, e)
        return errors

    def _begin_operation(self, buffer):
        with self.operation_lock:
            self.operation_name = type(buffer).__name__
            self.operation_started_at = time.time()
            self.operation_started_monotonic = time.monotonic()

    def _end_operation(self):
        with self.operation_lock:
            self.operation_name = ""
            self.operation_started_at = 0.0
            self.operation_started_monotonic = 0.0

    def get_status(self):
        with self.operation_lock:
            operation_name = self.operation_name
            operation_started_at = self.operation_started_at
            operation_started_monotonic = self.operation_started_monotonic
        operation_age = (
            max(time.monotonic() - operation_started_monotonic, 0.0)
            if operation_name else None)
        stalled = bool(operation_name and operation_age is not None
                       and operation_age > CAPTURE_SAVE_STALL_SECONDS)
        with self.queue_memory_lock:
            queued_bytes = self.queued_bytes
        return {
            "alive": self.is_alive(),
            "running": self.running,
            "queueSize": self._queue_size(),
            "queueMaxSize": self.queue.maxsize,
            "queuedBytes": queued_bytes,
            "queueMaxBytes": CAPTURE_SAVE_QUEUE_MAX_BYTES,
            "droppedBuffers": self.dropped_buffers,
            "operation": operation_name,
            "operationStartedAt": operation_started_at,
            "operationAge": operation_age,
            "stallAfter": CAPTURE_SAVE_STALL_SECONDS,
            "stalled": stalled,
            "lastSavedAt": self.last_saved_at,
            "lastSaveError": self.last_save_error,
        }

    def run(self):
        while True:
            data = self.queue.get()
            if data is None:
                break
            buffer_bytes = self._buffer_nbytes(data)
            self._begin_operation(data)
            try:
                save_errors = self.save(data)
                self.last_saved_at = time.time()
                self.last_save_error = "; ".join(save_errors or [])
            except Exception as e:
                self.last_save_error = str(e)
                logger.exception(
                    "capture save worker failed: camera=%s buffer_type=%s coil_id=%s index=%s error=%s",
                    self.name,
                    type(data).__name__,
                    getattr(data, "coilId", ""),
                    getattr(data, "save_index", ""),
                    e,
                )
            finally:
                self._end_operation()
                self._release_queue_memory(buffer_bytes)
                # This worker blocks in queue.get() between triggers. Do not
                # let its frame keep the previous large camera buffer alive
                # while the queue is empty.
                data = None
                buffer_bytes = 0
        self.running = False
