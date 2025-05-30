import json
import os
import shutil
import time
from pathlib import Path

import psutil
from PySide6 import QtCore
from PySide6.QtCore import Slot

from MonitorBase.MonitorBase import MonitorBase

import CONFIG

def is_root_path(path):
    # 标准化路径
    normalized_path = os.path.normpath(path)

    # 检查路径是否为根路径
    if os.name == 'nt':  # Windows 系统
        # Windows 中根路径通常是驱动器字母后跟 ":\"
        return bool(len(normalized_path) == 3 and normalized_path[1:3] == ':\\')
    else:  # POSIX 系统，如 UNIX/Linux
        # POSIX 系统中的根路径是 "/"
        return normalized_path == '/'


def tryGetInt(number):
    try:
        return int(number)
    except:
        return -1


class DiskMonitor(MonitorBase):
    def __init__(self, parent=None):
        log_folder = CONFIG.disk_monitor_log_dir
        config_f = CONFIG.disk_monitor_config
        super().__init__(config_f, log_folder, parent)
        self.fullData = {}
        self.init_monitor_data()

    def init_monitor_data(self):
        for mountpoint in self.monitorData:
            for index in range(len(self.monitorData[mountpoint]["monitor"])):
                item = self.monitorData[mountpoint]["monitor"][index]
                item.update(self.getDefault(item["source"]))
                print(item)
                self.monitorData[mountpoint]["monitor"][index] = item

    def delete_(self, folder_path, sort_type="time", delete_type="%", delete_size=10, minCount=0):
        # 获取文件夹中所有文件和文件夹的完整路径
        if is_root_path(folder_path):
            self.log.error(f"错误 无法 监听根路径！ {folder_path}")
            return
        entries = [os.path.join(folder_path, entry) for entry in os.listdir(folder_path)]
        # 如果文件夹为空，就没有什么可以删除的
        if not entries or len(entries) <= minCount:
            self.log.debug(f"无法完成删除！无文件 count {len(entries)} minCount {minCount}")
            return
        # 获取每个文件/文件夹的修改时间，并与其路径一起存储
        file_list = []
        sort_keys = []
        if sort_type == "time":
            entries = [(entry, os.path.getmtime(entry)) for entry in entries]
            # 按修改时间排序
            entries.sort(key=lambda x: x[1])
            file_list, sort_keys = zip(*entries)
        elif sort_type == "number":
            entries = [(entry, tryGetInt(entry)) for entry in entries]
            entries.sort(key=lambda x: x[1])
            file_list, sort_keys = zip(*entries)
        elif sort_type == "chart":
            entries = [(entry, str(os.path.basename(entry))) for entry in entries]
            entries.sort(key=lambda x: x[1])
            file_list, sort_keys = zip(*entries)
        # 获取最老的文件/文件夹
        if delete_type == "%":
            del_count = int(len(file_list) * delete_size / 100 + 1)
        else:
            del_count = int(delete_size)
        if len(file_list) - del_count < minCount:
            del_count = max(len(file_list) - minCount, 0)
        for oldest_entry in file_list[:del_count]:
            try:
                if os.path.isdir(oldest_entry):
                    shutil.rmtree(oldest_entry)
                    self.log.debug(f"移除 {oldest_entry}")
                else:
                    os.remove(oldest_entry)
                    self.log.debug(f"移除 {oldest_entry}")
            except BaseException as e:
                self.log.debug(f"移除失败 {oldest_entry}  {e}")

    @Slot(result=dict)
    def get_full_disk_info(self):
        """获取系统中所有磁盘的详细信息。"""
        disk_data = {}
        # 获取磁盘分区信息
        partitions = psutil.disk_partitions(all=True)
        for partition in partitions:
            usage = psutil.disk_usage(partition.mountpoint)
            threshold = 91
            if partition.mountpoint in self.monitorData:
                if "threshold" in self.monitorData[partition.mountpoint]:
                    threshold = self.monitorData[partition.mountpoint]["threshold"]
            disk_data[partition.device] = {
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "opts": partition.opts,
                "total": usage.total / (1024 ** 3),  # 总空间(GB)
                "used": usage.used / (1024 ** 3),  # 已用空间(GB)
                "free": usage.free / (1024 ** 3),  # 空闲空间(GB)
                "percentage": usage.percent,  # 使用率(%)
                "threshold": int(threshold)
            }
        return disk_data

    def run(self):
        while True:
            self.fullData = self.get_full_disk_info()
            for key in self.monitorData:
                monitorItem = self.monitorData[key]
                for monitor in monitorItem["monitor"]:
                    if key in self.fullData:
                        diskInfo = self.fullData[key]
                        if diskInfo["percentage"] > monitorItem["threshold"]:
                            path = monitor["source"]
                            monitorAble = monitor.get("monitorAble", False)
                            sort_type = monitor.get("sort_type", "time")

                            if not Path(path).exists():
                                continue
                            if monitorAble:
                                self.delete_(path, sort_type)
                        else:
                            print("未超过阈值")
            time.sleep(5)

    @Slot(str, result=list)
    def getDiskMonitorData(self, mountpoint):
        if mountpoint in self.monitorData:
            return self.monitorData[mountpoint]["monitor"]
        return []

    @Slot(str, result=dict)
    def getDefault(self, path):


        path = path.replace("file:///", "")
        return {
            "source": path,
            "sort_type": "time",
            "delete_type": "%",  # 删除类型
            "delete_size": 10,  # 删除数量/百分比
            "minCount": 0,  # 最小保留
            "monitorAble": True
        }

    @Slot(QtCore.QJsonValue)
    def addApp(self, app: QtCore.QJsonValue):
        app = app.toVariant()
        self.log.debug("添加数据" + json.dumps(app, indent=4, ensure_ascii=False))
        print(app)
        drive = Path(app["source"]).drive + "\\"
        # self.monitorData.append(app)
        if drive in self.monitorData:
            self.monitorData[drive]["monitor"].append(self.getDefault(app["source"]))
        else:
            self.monitorData[drive] = {
                "threshold": 90,
                "monitor": [self.getDefault(app["source"])]
            }
        self.set_config_change(True)
