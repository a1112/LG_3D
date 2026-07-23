import os
import subprocess

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

    @Slot(str, result=int)
    def system_(self, cmd):
        print("cmd:", cmd)
        try:
            return subprocess.Popen(str(cmd), shell=False, close_fds=True).pid
        except OSError:
            try:
                os.startfile(str(cmd))
                return 0
            except OSError as e:
                print("cmd error:", e)
                return -1

# {'name': 'cmd.exe', 'ppid': 10664,
#  'username': 'DESKTOP-TEM8G6F\\dell',
#  'create_time': 1748598233.855297, 'cpu_percent': 0.0,
#  'memory_percent': 0.0036973477283803423, 'exe': 'C:\\Windows\\System32\\cmd.exe',
#  'cmdline': ['C:\\Windows\\system32\\cmd.exe', '/c', 'D:\\LCX_USER\\LG_3D\\采集\\Cap2d.bat '],
#  'status': 'running', 'cwd': 'D:\\LCX_USER\\LG_3D\\采集'}


