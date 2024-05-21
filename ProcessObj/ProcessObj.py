import os

import psutil
from PySide6.QtCore import QObject, Signal, Slot


class ProcessObj(QObject):
    # 定义一个信号
    resultChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result = 0

    @Slot(int, int)
    def add(self, a, b):
        print("ProcessObj")
        result = a + b
        if result != self._result:
            self._result = result
            self.resultChanged.emit(self._result)

    @Slot(result=str)
    def getProcessList(self):
        return []

    @Slot(str)
    def system_(self, cmd):
        print("cmd:", cmd)
        return os.system(cmd)
        # return subprocess.Popen(cmd)


allAttrs = ['pid', 'name', 'ppid',
            'username', 'create_time', 'cpu_percent',
            'memory_percent',
            'exe', 'cmdline', 'status', 'cwd'
            ]


def getProcessDict():
    process = getProcess()
    processDict = {}

    for pro in process:
        if "exe" in pro:
            processDict[os.path.normpath(pro["exe"])] = pro
    return processDict


def getProcess():
    all_processes_ = psutil.process_iter()
    all_processes_ = list(all_processes_)
    return [toDict(process) for process in all_processes_]


def toDict(process: psutil.Process):
    processDict = {}
    for attr in allAttrs:
        try:
            attrValue = getattr(process, attr)()
            processDict[attr] = attrValue
        except Exception as e:
            pass
    return processDict
