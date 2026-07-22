"""
Combined capture entry point for 3D point cloud and 2D area cameras.
"""
import sys
import time
from pathlib import Path
from threading import Event

APP_DIR = Path(__file__).resolve().parents[1]
PACKAGE_DIR = APP_DIR.parent / "package" / "CoilDataBase"
for path in (APP_DIR, PACKAGE_DIR):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

import CONFIG
from CapTure import CapTure
import Signal
import Server
from Log import logger

CAPTURE_SUPERVISOR_INTERVAL = 1.0
CAPTURE_RESTART_MAX_DELAY = 30.0
CAPTURE_RESTART_STABLE_SECONDS = 30.0


def _camera_key(cap):
    camera_info = getattr(cap, "cameraInfo", None)
    if camera_info is not None:
        return getattr(camera_info, "key", "")
    raw_config = getattr(cap, "camera_info", None)
    if isinstance(raw_config, dict):
        return raw_config.get("key", "")
    return getattr(raw_config, "key", "")


def start_capture_workers(cap_list):
    started = []
    for cap in cap_list:
        try:
            cap.start()
            started.append(cap)
        except Exception as e:
            logger.exception(
                "capture worker failed to start; other cameras will continue: camera=%s error=%s",
                _camera_key(cap),
                e,
            )
    return started


def _restart_capture_worker(cap):
    replacement = CapTure(
        cap.camera_info,
        start_camera_server=getattr(cap, "start_camera_server", False),
    )
    replacement.start()
    return replacement


def supervise_capture_workers(cap_list,
                              stop_event,
                              cap_map=None,
                              interval=CAPTURE_SUPERVISOR_INTERVAL):
    restart_failures = {}
    next_restart_at = {}
    last_restart_at = {}
    while not stop_event.wait(timeout=interval):
        for index, cap in enumerate(tuple(cap_list)):
            camera_key = _camera_key(cap)
            if cap.ident is not None and cap.is_alive():
                restarted_at = last_restart_at.get(camera_key)
                if (restarted_at is not None
                        and time.monotonic() - restarted_at
                        >= CAPTURE_RESTART_STABLE_SECONDS):
                    restart_failures.pop(camera_key, None)
                    next_restart_at.pop(camera_key, None)
                    last_restart_at.pop(camera_key, None)
                continue

            now = time.monotonic()
            if now < next_restart_at.get(camera_key, 0):
                continue
            logger.error(
                "camera capture worker stopped; rebuilding worker: camera=%s service_error=%s",
                camera_key,
                getattr(cap, "service_error", ""),
            )
            try:
                failures = restart_failures.get(camera_key, 0) + 1
                delay = min(2**min(failures - 1, 5), CAPTURE_RESTART_MAX_DELAY)
                replacement = _restart_capture_worker(cap)
                cap_list[index] = replacement
                if cap_map is not None and camera_key:
                    cap_map[camera_key] = replacement
                restart_failures[camera_key] = failures
                last_restart_at[camera_key] = now
                next_restart_at[camera_key] = now + delay
                logger.warning(
                    "camera capture worker restarted: camera=%s attempt=%s",
                    camera_key,
                    failures,
                )
            except Exception as e:
                restart_failures[camera_key] = failures
                next_restart_at[camera_key] = now + delay
                logger.exception(
                    "camera capture worker restart failed: camera=%s retry_in_s=%.1f error=%s",
                    camera_key,
                    delay,
                    e,
                )


def stop_capture_workers(cap_list):
    for cap in cap_list:
        try:
            cap.release()
        except Exception as e:
            logger.exception(
                "camera capture service cleanup failed: camera=%s error=%s",
                _camera_key(cap),
                e,
            )
    for cap in cap_list:
        if cap.ident is None:
            continue
        cap.join(timeout=5)
        if cap.is_alive():
            logger.warning("camera capture service did not stop: camera=%s",
                           _camera_key(cap))


def main():
    CONFIG.set_console_mode_none()
    logger.debug("Starting combined CapTrue 3D + 2D capture")
    cap_list = [
        CapTure(camera_config.config, start_camera_server=False)
        for camera_config in CONFIG.capTureConfig.camera_config_list
    ]
    cap_map = {
        camera_config.key: cap
        for camera_config, cap in zip(CONFIG.capTureConfig.camera_config_list,
                                      cap_list)
    }
    logger.debug(
        "Starting unified capture API on %s:%s",
        CONFIG.capTureConfig.apiServerIp,
        CONFIG.capTureConfig.apiServerPort,
    )
    Server.start_capture_api(CONFIG.capTureConfig, cap_map)

    logger.debug("Starting capture signal listener")
    Signal.signal.start()
    while not Signal.signal.coil:
        time.sleep(0.1)

    logger.debug("Starting capture workers: %s", cap_list)
    start_capture_workers(cap_list)
    stop_event = Event()
    try:
        # Keep the process lifetime independent from the API and individual
        # camera threads. A failed camera must never make all daemon capture
        # workers disappear because the last foreground thread returned.
        supervise_capture_workers(cap_list, stop_event, cap_map=cap_map)
    except KeyboardInterrupt:
        logger.info("capture service shutdown requested")
    finally:
        stop_event.set()
        stop_capture_workers(cap_list)


if __name__ == "__main__":
    main()
