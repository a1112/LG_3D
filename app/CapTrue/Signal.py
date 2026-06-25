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
        super().__init__(daemon=True)
        self.url = url
        self.coil:SecondaryCoil|None = None
        self.regFunc = []

    def _trigger(self, event_name):
        for func in list(self.regFunc):
            try:
                func(event_name, self.coil)
            except Exception as e:
                logger.exception("signal callback failed: event=%s func=%s error=%s", event_name, func, e)

    def triggerInit(self):
        self._trigger("init")

    def triggerIn(self):
        self._trigger("in")

    def triggerOut(self):
        self._trigger("out")

    def register(self,func):
        self.regFunc.append(func)
        if self.coil is not None:
            try:
                func("init", self.coil)
            except Exception as e:
                logger.exception("signal callback init failed: func=%s error=%s", func, e)

    def run(self):
        while True:
            try:
                coil = Coil.get_last_coil()
                if coil is None:
                    logger.debug("signal polling found no coil")
                    time.sleep(1)
                    continue
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
