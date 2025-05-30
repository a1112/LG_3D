import copy
import json
import os
import sys
from threading import Thread

from PySide6 import QtCore
from PySide6.QtCore import QObject, Slot, Signal, Property

from Log import DailyLogger


class MonitorBase(QObject, Thread):
    def __init__(self, configF, logFolder, parent=None):
        self.hasChange = False
        super().__init__(parent)
        Thread.__init__(self)
        self.configF = configF
        self.logFolder = logFolder
        self.log = DailyLogger(logFolder)
        self.configFile = configF if "python.exe" in sys.executable else os.path.join(
            os.path.dirname(sys.executable), configF)

        self.log.info(f"--------------------------开始运行--------------------------")

        if not os.path.exists(self.configFile):
            self.log.info(f"配置文件不存在,创建配置文件")
            json.dump({}, open(self.configFile, "w", encoding='utf-8'), ensure_ascii=False, indent=4)

        self.monitorData = json.load(open(self.configFile, "r", encoding='utf-8'))
        self.monitorData_old = copy.deepcopy(self.monitorData)
        self.stateDict = {}
        self.start()

    @Slot()
    def saveConfig(self):
        self.log.debug("保存配置")
        self.monitorData_old = copy.deepcopy(self.monitorData)
        json.dump(self.monitorData, open(self.configFile, "w", encoding='utf-8'), ensure_ascii=False, indent=4)
        self.set_config_change(False)

    @Slot(result=str)
    def getConfigPath(self):
        return os.path.abspath(self.configFile)

    @Slot(result=str)
    def getConfigDirPath(self):
        return os.path.dirname(os.path.abspath(self.configFile))

    @Slot(str, result=str)
    def dirName(self, path):
        return os.path.dirname(path)

    @Slot(result=str)
    def getLogPath(self):
        return os.path.abspath(self.logFolder)

    @Slot(result=str)
    def getMonitor(self):
        return json.dumps(self.monitorData)

    def get_config_change(self):
        return self.hasChange

    def set_config_change(self, value):
        if self.hasChange != value:
            self.hasChange = value
            self.configChanged.emit()

    configChanged = Signal()
    configHasChanged = Property(bool, get_config_change, set_config_change, notify=configChanged)
