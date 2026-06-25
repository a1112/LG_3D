"""
Combined capture entry point for 3D point cloud and 2D area cameras.
"""
import sys
import time
from pathlib import Path

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


def main():
    CONFIG.set_console_mode_none()
    logger.debug("Starting combined CapTrue 3D + 2D capture")
    cap_list = [
        CapTure(camera_config.config, start_camera_server=False)
        for camera_config in CONFIG.capTureConfig.camera_config_list
    ]
    cap_map = {camera_config.key: cap for camera_config, cap in zip(CONFIG.capTureConfig.camera_config_list, cap_list)}
    logger.debug(
        f"Starting unified capture API on "
        f"{CONFIG.capTureConfig.apiServerIp}:{CONFIG.capTureConfig.apiServerPort}"
    )
    Server.start_capture_api(CONFIG.capTureConfig, cap_map)

    logger.debug("Starting capture signal listener")
    Signal.signal.start()
    while not Signal.signal.coil:
        time.sleep(0.1)

    logger.debug("Starting capture workers: %s", cap_list)
    for cap in cap_list:
        cap.start()
    for cap in cap_list:
        cap.join()


if __name__ == "__main__":
    main()
