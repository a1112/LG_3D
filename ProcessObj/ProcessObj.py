import os

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

# {'name': 'cmd.exe', 'ppid': 10664,
#  'username': 'DESKTOP-TEM8G6F\\dell',
#  'create_time': 1748598233.855297, 'cpu_percent': 0.0,
#  'memory_percent': 0.0036973477283803423, 'exe': 'C:\\Windows\\System32\\cmd.exe',
#  'cmdline': ['C:\\Windows\\system32\\cmd.exe', '/c', 'D:\\LCX_USER\\LG_3D\\采集\\Cap2d.bat '],
#  'status': 'running', 'cwd': 'D:\\LCX_USER\\LG_3D\\采集'}


