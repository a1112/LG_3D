import time
from threading import Thread
import CONFIG
from CoilDataBase import Coil
from CoilDataBase.models import SecondaryCoil

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
            except:
                raise
            time.sleep(3)


signal = Signal(CONFIG.capTureConfig.signalUrl)
