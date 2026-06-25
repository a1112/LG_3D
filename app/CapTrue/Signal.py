import time
from threading import Thread
import CONFIG
from CoilDataBase import Coil
from CoilDataBase.models.SecondaryCoil import SecondaryCoil
from Log import logger

lastTimeDict = {
    "t":0
}


class Signal(Thread):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.coil:SecondaryCoil|None = None
        self.regFunc = []

    def triggerInit(self):
        for func in self.regFunc:
            func("init", self.coil)

    def triggerIn(self):
        for func in self.regFunc:
            func("in", self.coil)

    def triggerOut(self):
        for func in self.regFunc:
            func("out", self.coil)

    def register(self,func):
        self.regFunc.append(func)
        if self.coil is not None:
            func("init", self.coil)

    def run(self):
        while True:
            try:
                coil = Coil.get_last_coil()
                if not self.coil:
                    self.coil = coil
                    self.triggerInit()
                if coil.CoilNo != self.coil.CoilNo:
                    self.coil = coil
                    while True:
                        max_time = max([lastTimeDict[t] for t in lastTimeDict])
                        if time.time() - max_time > 3:
                            self.triggerIn()
                            break
                        time.sleep(1)
            except Exception as e:
                logger.warning("signal polling failed: %s", e)
            time.sleep(1)


signal = Signal(CONFIG.capTureConfig.signalUrl)
