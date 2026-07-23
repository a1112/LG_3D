import os
import time
from pathlib import Path
from threading import Thread

from PySide6.QtCore import QObject, Slot, Signal, Property


def format_size(bytes, precision=2):
    """ 根据字节大小自动转换为合适的单位，并保留指定的小数位数 """
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']
    if bytes == 0:
        return '0 B'
    size = float(bytes)
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f"{size:.{precision}f} {units[index]}"


def get_folder_size(directory):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size


class PathInfo(QObject, Thread):
    def __init__(self, parent=None):
        super().__init__(parent)
        Thread.__init__(self)
        self.daemon = True
        self._running = True
        self._path = ""
        self._exists = False
        self._content = 0
        self._size = 0  # GB
        self.start()

    def setPath(self, path):
        if path != self._path:
            self._path = path
            self.pathChanged.emit(path)

    def getPath(self):
        return self._path

    pathChanged = Signal(str)
    path = Property(str, getPath, setPath, notify=pathChanged)

    def setExists(self, exists):
        if exists != self._exists:
            self._exists = exists
            self.existsChanged.emit(exists)

    def getExists(self):
        return self._exists

    existsChanged = Signal(bool)
    exists = Property(bool, getExists, setExists, notify=existsChanged)

    def setContent(self, content):
        if content != self._content:
            self._content = content
            self.contentChanged.emit(content)

    def getContent(self):
        return self._content

    contentChanged = Signal(int)
    content = Property(int, getContent, setContent, notify=contentChanged)

    def setSize(self, size):
        if size != self._size:
            self._size = size
            self.sizeChanged.emit(size)

    def getSize(self):
        return self._size

    sizeChanged = Signal(int)
    size = Property(int, getSize, setSize, notify=sizeChanged)

    def run(self):
        while self._running:
            path = Path(self._path)
            self.setExists(path.exists())
            if path.exists():
                try:
                    self.setContent(len(list(path.iterdir())))
                    self.setSize(get_folder_size(str(path)))  # path.stat().st_size)
                except (OSError, PermissionError):
                    self.setContent(0)
                    self.setSize(0)
            else:
                self.setContent(0)
                self.setSize(0)  # path.stat().st_size)
            time.sleep(5)

    @Slot()
    def stop(self):
        self._running = False
