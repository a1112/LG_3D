"""
 入口


"""
import ctypes
import time

kernel32 = ctypes.windll.kernel32
kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), (0x4 | 0x80 | 0x20 | 0x2 | 0x10 | 0x1 | 0x00 | 0x100))


import CONFIG
from Log import logger


logger.debug("启动采集... ...")

from CapTure import CapTure
import Signal
from Log import logger


def main():
    logger.debug("启动... ...")
    cap_list = []
    for camera_config in CONFIG.capTureConfig.camera_config_list:
        cap_list.append(CapTure(camera_config.config))
    logger.debug("启动信号... ...")
    Signal.signal.start()
    while not Signal.signal.coil:
        time.sleep(0.01)
        pass
    logger.debug(f"启动采集... ...{cap_list}")
    for cap in cap_list:
        cap.start()
    input()


if __name__ == "__main__":
    main()
