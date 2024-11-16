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
    capList = []
    for cameraInfo in CONFIG.CapTureConfig["camera"]:
        capList.append(CapTure(cameraInfo))
    logger.debug("启动信号... ...")
    Signal.signal.start()
    while not Signal.signal.coil:
        time.sleep(0.01)
        pass
    logger.debug("启动采集... ...")
    for cap in capList:
        cap.start()
    input()


if __name__ == "__main__":
    main()
