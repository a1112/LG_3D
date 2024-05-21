# This Python file uses the following encoding: utf-8
import sys
import os
from pathlib import Path

from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from DiskMonitor.DiskMonitor import DiskMonitor
from DiskMonitor.PathInfo import PathInfo
from ProcessObj.ProcessObj import ProcessObj
from ProcessObj.SoftMonitor import SoftMonitor
from tools.IconImageProvider import IconImageProvider
from SoftList import SoftList


class OS(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._os = sys.platform

    @Slot(str)
    def system(self, cmd):
        os.system(cmd)


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    qmlRegisterType(ProcessObj, 'ProcessObj', 1, 0, 'ProcessObj')
    qmlRegisterType(SoftList, 'SoftList', 1, 0, 'SoftList')
    qmlRegisterType(SoftMonitor, 'SoftMonitor', 1, 0, 'SoftMonitor')
    qmlRegisterType(DiskMonitor, 'DiskMonitor', 1, 0, 'DiskMonitor')
    qmlRegisterType(PathInfo, 'DiskMonitor', 1, 0, 'PathInfo')
    engine = QQmlApplicationEngine()
    engine.addImageProvider("icon", IconImageProvider())
    qml_file = Path(__file__).resolve().parent / "main.qml"
    engine.rootContext().setContextProperty("Os", OS())
    engine.load(qml_file)
    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec())
