import copy
import json
import os
from pathlib import Path
from threading import Thread

from PySide6 import QtCore
from PySide6.QtCore import QObject, Slot, Signal, Property

from lg3d_service_monitor.logging_utils import DailyLogger


class MonitorBase(QObject, Thread):
    def __init__(self, configF, logFolder, parent=None, default_data=None):
        self.hasChange = False
        super().__init__(parent)
        Thread.__init__(self)
        self.daemon = True
        self._running = True
        self.configF = str(configF)
        self.logFolder = str(logFolder)
        self.log = DailyLogger(self.logFolder)
        self.configFile = str(Path(configF).resolve())

        self.log.info(f"--------------------------开始运行--------------------------")

        if not os.path.exists(self.configFile):
            self.log.info(f"配置文件不存在,创建配置文件")
            os.makedirs(os.path.dirname(os.path.abspath(self.configFile)), exist_ok=True)
            initial_data = copy.deepcopy(
                default_data) if default_data is not None else {}
            with open(self.configFile, "w", encoding='utf-8') as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=4)

        with open(self.configFile, "r", encoding='utf-8') as f:
            self.monitorData = json.load(f)
        self.monitorData_old = copy.deepcopy(self.monitorData)
        self.stateDict = {}

    @Slot()
    def saveConfig(self):
        self.log.debug("保存配置")
        self.monitorData_old = copy.deepcopy(self.monitorData)
        os.makedirs(os.path.dirname(os.path.abspath(self.configFile)), exist_ok=True)
        with open(self.configFile, "w", encoding='utf-8') as f:
            json.dump(self.monitorData, f, ensure_ascii=False, indent=4)
        self.set_config_change(False)

    @Slot()
    def stop(self):
        self._running = False

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
