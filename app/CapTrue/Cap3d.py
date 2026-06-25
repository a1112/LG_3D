"""
 入口
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
import Global
from CapTure import CapTure
import Signal
from Log import logger


def main():
    CONFIG.set_console_mode_none()
    logger.debug("启动...  CapTrue ...")
    cap_list = []
    for camera_config in CONFIG.capTureConfig.camera_config_list:
        camera_config.config["cap2D"] = False
        Global.USE_2D = False
        cap_list.append(CapTure(camera_config.config))
    logger.debug("启动信号... ...")
    Signal.signal.start()
    while not Signal.signal.coil:
        time.sleep(0.1)
    logger.debug("启动采集... ...%s", cap_list)
    for cap in cap_list:
        cap.start()
    for cap in cap_list:
        cap.join()


if __name__ == "__main__":
    main()
