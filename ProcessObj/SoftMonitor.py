import copy
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from threading import Thread
from pathlib import Path
import win32api
import win32gui
from PySide6 import QtCore
from PySide6.QtCore import QObject, Slot, Signal, Property
from collections import defaultdict
from Log import DailyLogger
from MonitorBase.MonitorBase import MonitorBase
from ProcessObj import tryGetInt
from tools.soft import getProcessDict, kill_process_and_children

import psutil

from configs.GlobSoftConfig import globSoftConfig
from enum_types.enums import SoftRunStateEnum


class SoftMonitor(MonitorBase):
    def __init__(self, parent=None):
        configF = "config/SoftMonitor.json"
        logFolder = "logs/SoftMonitor"
        super().__init__(configF, logFolder, parent)

    def _start_exe_(self, exe, args):
        self.log.info(f"执行 \"{exe}\" {args}")
        exe_url = Path(exe)
        #win32gui.GetDesktopWindow()
        pid = win32api.ShellExecute(win32gui.GetDesktopWindow(), 'runas', exe, args, str(exe_url.parent), 1)
        # os.startfile(exe)
        return pid
        # return 0

        # # Windows 特定标志
        # creationflags = 0
        # if sys.platform == "win32":
        #     # 使用以下标志确保子进程独立运行
        #     creationflags = (
        #             subprocess.CREATE_NEW_PROCESS_GROUP |
        #             subprocess.DETACHED_PROCESS |
        #             subprocess.CREATE_NO_WINDOW  # 可选：隐藏控制台窗口
        #     )
        #
        # # 启动程序（不等待结束）
        # process = subprocess.Popen(
        #     [exe, args],
        #     shell=False  # 重要：设置为 False
        # )

    # 立即返回，不等待程序结束
    # Python 脚本可以继续执行或直接退出

    @Slot(str, result=int)
    def getState_(self, name):
        if name in self.stateDict:
            return self.stateDict[name]
        return -2

    @Slot(str)
    def stopExe(self, exe):
        name = Path(exe).name
        self.log.debug(f"主动关闭 {name} {exe}")

        pid_list = globSoftConfig.get_pip_list(exe)
        print(f"<UNK> pid_list {pid_list} <UNK>")
        # for pid in pid_list:
        #     kill_process_and_children(pid)
        #     return os.system(f"taskkill /F / PID {pid} /T")

        # if ".exe" in name:
        #     return os.system(f"taskkill /F /IM {name} /T")
        return 0

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
        self.log.debug("全部关闭。")
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
            print(processDict)
            for item in self.monitorData:
                name = item["name"]
                exe = os.path.normpath(item["exe"])
                args = item["args"] if "args" in item else ""
                delay = tryGetInt(item["delay"]) if "delay" in item else 5
                monitor = item["monitorAble"] if "monitorAble" in item else True

                ppid = 0

                if not Path(exe).exists():
                    self.log.error(f"{name}  不存在 {exe} {args}  延时 {delay}")
                    self.stateDict[name] = SoftRunStateEnum.NULL
                    continue
                if exe not in processDict:
                    self.stateDict[name] = SoftRunStateEnum.STOPPED
                    self.log.debug(f"{name}  未运行  {exe} {args}  延时 {delay}  监听 {monitor}")
                    if monitor:
                        time.sleep(delay)
                        self.log.debug(f"{name}  启动  {exe} {args}  延时 {delay}  监听 {monitor}")
                        self._start_exe_(exe, args)
                        self.stateDict[name] = SoftRunStateEnum.RUNNING
                    continue
                else:
                    process = processDict[exe]
                    ppid = process["ppid"]
                    self.stateDict[name] = SoftRunStateEnum.RUNNING
                globSoftConfig.set_soft_state(exe, ppid, self.stateDict[name])

                # 运行该软件
            time.sleep(3)
