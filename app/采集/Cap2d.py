"""
 入口
"""
import time
import CONFIG
from CapTure import CapTure
import Signal
from Log import logger
import Global

def main():
    CONFIG.set_console_mode_none()
    logger.debug("启动...  采集 ...")
    cap_list = []
    for camera_config in CONFIG.capTureConfig.camera_config_list:
        camera_config.config["cap3D"] = False
        Global.USE_3D = False
        cap_list.append(CapTure(camera_config.config))
    logger.debug("启动信号... ...")
    Signal.signal.start()
    while not Signal.signal.coil:
        time.sleep(0.1)
        pass
    logger.debug(f"启动采集... ...{cap_list}")
    for cap in cap_list:
        cap.start()
    for cap in cap_list:
        cap.join()


if __name__ == "__main__":
    main()
