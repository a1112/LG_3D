import os
import time
from threading import Lock, Thread
import CONFIG
from CoilDataBase import Coil
from CoilDataBase.models.SecondaryCoil import SecondaryCoil
from Log import logger

lastTimeDict = {
    "t":0
}
SIGNAL_SWITCH_MAX_WAIT_SECONDS = max(
    1.0, float(os.getenv("LG3D_SIGNAL_SWITCH_MAX_WAIT_SECONDS", "30.0")))
SIGNAL_POLL_STALL_SECONDS = max(
    1.0, float(os.getenv("LG3D_SIGNAL_POLL_STALL_SECONDS", "60.0")))
SIGNAL_CALLBACK_STALL_SECONDS = max(
    1.0, float(os.getenv("LG3D_SIGNAL_CALLBACK_STALL_SECONDS", "60.0")))


def _latest_capture_time():
    # Camera workers add their key lazily. tuple() can observe a concurrent
    # dict resize, so retry the snapshot rather than losing the coil switch.
    while True:
        try:
            values = tuple(lastTimeDict.values())
            return max(values, default=0.0)
        except RuntimeError:
            time.sleep(0)


class Signal(Thread):
    def __init__(self, url):
        super().__init__(daemon=True)
        self.url = url
        self.coil:SecondaryCoil|None = None
        self.regFunc = []
        self.poll_attempts = 0
        self.last_poll_started_at = 0.0
        self.last_poll_started_monotonic = 0.0
        self.last_poll_completed_at = 0.0
        self.last_poll_error = ""
        self._activity_lock = Lock()
        self._activities = {}

    def _begin_activity(self, name):
        token = object()
        with self._activity_lock:
            self._activities[token] = (
                str(name),
                time.time(),
                time.monotonic(),
            )
        return token

    def _end_activity(self, token):
        with self._activity_lock:
            self._activities.pop(token, None)

    def get_status(self):
        poll_age = (max(time.monotonic() - self.last_poll_started_monotonic,
                        0.0) if self.last_poll_started_monotonic else None)
        with self._activity_lock:
            activities = list(self._activities.values())
        if activities:
            activity_name, activity_started_at, activity_started_monotonic = min(
                activities, key=lambda item: item[2])
            activity_age = max(
                time.monotonic() - activity_started_monotonic, 0.0)
        else:
            activity_name = ""
            activity_started_at = 0.0
            activity_age = None
        poll_stalled = bool(poll_age is not None
                            and poll_age > SIGNAL_POLL_STALL_SECONDS)
        activity_stalled = bool(
            activity_age is not None
            and activity_age > SIGNAL_CALLBACK_STALL_SECONDS)
        return {
            "alive": self.is_alive(),
            "pollAttempts": self.poll_attempts,
            "lastPollStartedAt": self.last_poll_started_at,
            "lastPollCompletedAt": self.last_poll_completed_at,
            "lastPollError": self.last_poll_error,
            "pollAge": poll_age,
            "stallAfter": SIGNAL_POLL_STALL_SECONDS,
            "pollStalled": poll_stalled,
            "activity": activity_name,
            "activityCount": len(activities),
            "activityStartedAt": activity_started_at,
            "activityAge": activity_age,
            "activityStallAfter": SIGNAL_CALLBACK_STALL_SECONDS,
            "activityStalled": activity_stalled,
            "stalled": poll_stalled or activity_stalled,
            "coilId": getattr(self.coil, "Id", None),
            "coilNo": getattr(self.coil, "CoilNo", ""),
        }

    def _trigger(self, event_name):
        activity_token = self._begin_activity(f"trigger_{event_name}")
        try:
            for func in list(self.regFunc):
                try:
                    func(event_name, self.coil)
                except Exception as e:
                    logger.exception(
                        "signal callback failed: event=%s func=%s error=%s",
                        event_name,
                        func,
                        e,
                    )
        finally:
            self._end_activity(activity_token)

    def triggerInit(self):
        self._trigger("init")

    def triggerIn(self):
        self._trigger("in")

    def triggerOut(self):
        self._trigger("out")

    def register(self,func):
        self.regFunc.append(func)
        if self.coil is not None:
            activity_token = self._begin_activity("register_init")
            try:
                func("init", self.coil)
            except Exception as e:
                logger.exception("signal callback init failed: func=%s error=%s", func, e)
            finally:
                self._end_activity(activity_token)

    def unregister(self, func):
        try:
            self.regFunc.remove(func)
        except ValueError:
            return False
        return True

    def run(self):
        while True:
            try:
                self.poll_attempts += 1
                self.last_poll_started_at = time.time()
                self.last_poll_started_monotonic = time.monotonic()
                try:
                    coil = Coil.get_last_coil()
                    self.last_poll_error = ""
                except Exception as e:
                    self.last_poll_error = str(e)
                    raise
                finally:
                    self.last_poll_completed_at = time.time()
                    self.last_poll_started_monotonic = 0.0
                if coil is None:
                    logger.debug("signal polling found no coil")
                    time.sleep(1)
                    continue
                if not self.coil:
                    self.coil = coil
                    self.triggerInit()
                if coil.CoilNo != self.coil.CoilNo:
                    wait_started = time.monotonic()
                    while True:
                        max_time = _latest_capture_time()
                        quiet = time.time() - max_time > 3
                        wait_age = time.monotonic() - wait_started
                        if quiet or wait_age >= SIGNAL_SWITCH_MAX_WAIT_SECONDS:
                            if not quiet:
                                logger.warning(
                                    "forcing coil switch after capture quiet timeout: old=%s new=%s wait_s=%.1f",
                                    getattr(self.coil, "CoilNo", ""),
                                    getattr(coil, "CoilNo", ""),
                                    wait_age,
                                )
                            self.triggerOut()
                            self.coil = coil
                            self.triggerIn()
                            break
                        time.sleep(1)
            except Exception as e:
                logger.warning("signal polling failed: %s", e)
            time.sleep(1)


signal = Signal(CONFIG.capTureConfig.signalUrl)
