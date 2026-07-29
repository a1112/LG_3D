"""
记录服务器日志

"""
from collections import deque
import os
from threading import RLock


def _message_history_limit() -> int:
    try:
        return max(int(os.getenv("LG3D_SERVER_MESSAGE_HISTORY", "1000")), 1)
    except ValueError:
        return 1000


class ServerMsg:
    """
    通讯，日志记录
    """

    def __init__(self):
        self.msgDict = {}
        self._messages = deque(maxlen=_message_history_limit())
        self._lock = RLock()

    @property
    def msgList(self):
        # Preserve the legacy JSON-serializable list interface while keeping
        # the retained history bounded internally.
        with self._lock:
            return list(self._messages)

    def addMsg(self, msgType, msg):
        with self._lock:
            self._messages.append([msgType, msg])
            self.msgDict[msgType] = msg

    def getLastMsg(self, msgType=None):
        with self._lock:
            if msgType:
                if msgType in self.msgDict:
                    return self.msgDict[msgType]
            elif self._messages:
                return self._messages[-1]
        return None

    def getAllType(self):
        with self._lock:
            return list(self.msgDict.keys())
