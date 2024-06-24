import copy
import json
import os
import sys
import time
from pathlib import Path
from threading import Thread

import win32api
import win32gui
from PySide6 import QtCore
from PySide6.QtCore import QObject, Slot, Signal, Property

from Log import DailyLogger
from MonitorBase.MonitorBase import MonitorBase
from ProcessObj import getProcessDict, tryGetInt


class SoftMonitor(MonitorBase):
    def __init__(self, parent=None):
        configF = "config/SoftMonitor.json"
        logFolder = "logs/SoftMonitor"
        super().__init__(configF, logFolder, parent)

    def _start_exe_(self, exe, args):
        self.log.info(f"执行 \"{exe}\" {args}")
        return win32api.ShellExecute(win32gui.GetDesktopWindow(), 'open', exe, args, '', 1)

    @Slot(str, result=int)
    def getState_(self, name):
        if name in self.stateDict:
            return self.stateDict[name]
        return -2

    @Slot(str)
    def stopExe(self, exe):
        name = Path(exe).name
        self.log.debug(f"主动关闭 {name} {exe}")
        return os.system(f"taskkill /F /IM {name} /T")

    @Slot(int, str, str)
    @Slot(int, str, bool)
    @Slot(int, str, int)
    def changeValue(self, index, key, value):
        self.log.info(f"修改 {index} {key} {value}")
        self.monitorData[index][key] = value
        self.set_config_change(self.monitorData != self.monitorData_old)

    @Slot(str)
    def startExe(self, name):
        for item in self.monitorData:
            if name == item["name"]:
                name = item["name"]
                exe = item["exe"]
                args = item["args"] if "args" in item else ""
                self.log.debug("主动启动 " + name + " " + exe + " " + args)
                self._start_exe_(exe, args)

    @Slot()
    def closeAll(self):
        self.log.debug("全部关闭。 ")
        for item in self.monitorData:
            exe = item["exe"]
            self.stopExe(exe)

    @Slot()
    def startAll(self):
        self.log.debug("全部启动。 ")
        processDict = getProcessDict()
        for item in self.monitorData:
            exe = os.path.normpath(item["exe"])
            if exe in processDict:
                continue
            args = item["args"] if "args" in item else ""
            monitor = item["monitorAble"] if "monitorAble" in item else True
            if monitor:
                self._start_exe_(exe, args)

    @Slot(str, result=QtCore.QJsonValue)
    def getDefault(self, exe: str):
        exe = exe.replace("file:///", "")
        return {
            "name": Path(exe).stem,
            "exe": exe,
            "args": "",
            "delay": 5,
            "monitorAble": True
        }

    @Slot(QtCore.QJsonValue)
    def addApp(self, app: QtCore.QJsonValue):
        app = app.toVariant()
        self.log.debug("添加数据" + json.dumps(app, indent=4, ensure_ascii=False))
        app["delay"] = tryGetInt(app["delay"])

        self.monitorData.append(app)
        self.set_config_change(True)

    @Slot(int)
    def remove(self, index):
        self.log.debug("移除数据" + json.dumps(self.monitorData[index], indent=4, ensure_ascii=False))
        self.monitorData.pop(index)
        self.set_config_change(True)

    @Slot(int, result=dict)
    def index(self, index):
        return self.monitorData[index]

    def run(self):
        while True:
            processDict = getProcessDict()
            for item in self.monitorData:
                name = item["name"]
                exe = os.path.normpath(item["exe"])
                args = item["args"] if "args" in item else ""
                delay = tryGetInt(item["delay"]) if "delay" in item else 5
                monitor = item["monitorAble"] if "monitorAble" in item else True
                if not Path(exe).exists():
                    self.log.error(f"{name}  不存在 {exe} {args}  延时 {delay}")
                    self.stateDict[name] = -1
                    continue
                if exe not in processDict:
                    self.stateDict[name] = 0
                    self.log.debug(f"{name}  未运行  {exe} {args}  延时 {delay}  监听 {monitor}")
                    if monitor:
                        time.sleep(delay)
                        self.log.debug(f"{name}  启动  {exe} {args}  延时 {delay}  监听 {monitor}")
                        self._start_exe_(exe, args)
                        time.sleep(1)
                    continue
                self.stateDict[name] = 1
                # 运行该软件
            time.sleep(4)
