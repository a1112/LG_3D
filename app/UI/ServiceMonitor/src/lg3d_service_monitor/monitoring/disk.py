import json
import os
import shutil
import time
from pathlib import Path

import psutil
from PySide6 import QtCore
from PySide6.QtCore import Slot

from lg3d_service_monitor.config.paths import (
    ensure_runtime_config,
    log_directory,
)
from lg3d_service_monitor.monitoring.base import MonitorBase


def is_root_path(path):
    # 标准化路径
    normalized_path = os.path.normpath(path)

    # 检查路径是否为根路径
    if os.name == 'nt':  # Windows 系统
        # Windows 中根路径通常是驱动器字母后跟 ":\"
        return bool(
            (len(normalized_path) == 2 and normalized_path[1] == ':') or
            (len(normalized_path) == 3 and normalized_path[1:3] == ':\\')
        )
    else:  # POSIX 系统，如 UNIX/Linux
        # POSIX 系统中的根路径是 "/"
        return normalized_path == '/'


def try_get_int(number):
    try:
        return int(number)
    except (TypeError, ValueError):
        return -1


class DiskMonitor(MonitorBase):
    def __init__(self, parent=None):
        log_folder = log_directory("DiskMonitor")
        config_f = ensure_runtime_config(
            "DiskMonitor.json",
            default_data={},
        )
        super().__init__(config_f, log_folder, parent, default_data={})
        self.fullData = {}
        self.init_monitor_data()
        self.start()

    def _normalize_path(self, path):
        path = str(path)
        if path.startswith("file:"):
            local_path = QtCore.QUrl(path).toLocalFile()
            return local_path or path.replace("file:///", "")
        return path

    def _normalize_mountpoint(self, mountpoint):
        mountpoint = self._normalize_path(mountpoint)
        mountpoint = os.path.normpath(mountpoint)
        if len(mountpoint) == 2 and mountpoint[1] == ":":
            mountpoint += "\\"
        return mountpoint

    def _mountpoint_for_source(self, source):
        source = self._normalize_path(source)
        drive = Path(source).drive
        if drive:
            return self._normalize_mountpoint(drive + "\\")
        return self._normalize_mountpoint(Path(source).anchor)

    def _normalize_monitor_item(self, item):
        default_item = self.get_default(item.get("source", ""))
        default_item.update(item)
        default_item["source"] = self._normalize_path(default_item["source"])
        default_item["delete_size"] = max(0, try_get_int(default_item.get("delete_size", 10)))
        default_item["minCount"] = max(0, try_get_int(default_item.get("minCount", 0)))
        default_item["sort_type"] = default_item.get("sort_type") or "time"
        default_item["delete_type"] = default_item.get("delete_type") or "%"
        default_item["monitorAble"] = bool(default_item.get("monitorAble", True))
        return default_item

    def init_monitor_data(self):
        normalized_data = {}
        for mountpoint, disk_config in self.monitorData.items():
            normalized_mountpoint = self._normalize_mountpoint(mountpoint)
            monitors = disk_config.get("monitor", [])
            normalized_data[normalized_mountpoint] = {
                "threshold": max(0, min(100, try_get_int(disk_config.get("threshold", 90)))),
                "monitor": [self._normalize_monitor_item(item) for item in monitors]
            }
        self.monitorData = normalized_data

    def delete_(self, folder_path, sort_type="time", delete_type="%", delete_size=10, minCount=0):
        # 获取文件夹中所有文件和文件夹的完整路径
        folder_path = self._normalize_path(folder_path)
        if is_root_path(folder_path):
            self.log.error(f"错误 无法 监听根路径！ {folder_path}")
            return
        if not os.path.isdir(folder_path):
            self.log.warning(f"无法清理，路径不是文件夹 {folder_path}")
            return
        minCount = max(0, try_get_int(minCount))
        delete_size = max(0, try_get_int(delete_size))
        if delete_size <= 0:
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
            entries = [(entry, try_get_int(os.path.basename(entry))) for entry in entries]
            entries.sort(key=lambda x: x[1])
            file_list, sort_keys = zip(*entries)
        elif sort_type == "chart":
            entries = [(entry, str(os.path.basename(entry))) for entry in entries]
            entries.sort(key=lambda x: x[1])
            file_list, sort_keys = zip(*entries)
        else:
            self.log.warning(f"未知排序方式 {sort_type}")
            return
        # 获取最老的文件/文件夹
        if delete_type == "%":
            delete_size = min(delete_size, 100)
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
            try:
                usage = psutil.disk_usage(partition.mountpoint)
            except (PermissionError, OSError) as e:
                self.log.warning(f"读取磁盘信息失败 {partition.mountpoint} {e}")
                continue
            threshold = 91
            mountpoint = self._normalize_mountpoint(partition.mountpoint)
            if mountpoint in self.monitorData:
                if "threshold" in self.monitorData[mountpoint]:
                    threshold = self.monitorData[mountpoint]["threshold"]
            disk_data[mountpoint] = {
                "device": partition.device,
                "mountpoint": mountpoint,
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
        while self._running:
            try:
                self.fullData = self.get_full_disk_info()
            except BaseException as e:
                self.log.error(f"<DiskMonitor> 获取磁盘信息失败 {e}")
                time.sleep(30)
                continue
            for key, monitorItem in list(self.monitorData.items()):
                try:
                    for monitor in list(monitorItem.get("monitor", [])):
                        if key in self.fullData:
                            diskInfo = self.fullData[key]
                            if diskInfo["percentage"] > monitorItem["threshold"]:
                                path = monitor["source"]
                                monitorAble = monitor.get("monitorAble", False)
                                sort_type = monitor.get("sort_type", "time")
                                delete_type = monitor.get("delete_type", "%")
                                delete_size = monitor.get("delete_size", 10)
                                min_count = monitor.get("minCount", 0)

                                if not Path(path).exists():
                                    continue
                                if monitorAble:
                                    self.delete_(path, sort_type, delete_type, delete_size, min_count)
                            else:
                                pass
                                # print("未超过阈值")
                except BaseException as e:
                    self.log.error(f"<DiskMonitor> {key}  {e}")
            time.sleep(30)

    @Slot(str, result=list)
    def get_disk_monitor_data(self, mountpoint):
        mountpoint = self._normalize_mountpoint(mountpoint)
        if mountpoint in self.monitorData:
            return self.monitorData[mountpoint]["monitor"]
        return []

    @Slot(str, result=list)
    def getDiskMonitorData(self, mountpoint):
        return self.get_disk_monitor_data(mountpoint)

    @Slot(str, result=dict)
    def get_default(self, path):
        path = self._normalize_path(path)
        return {
            "source": path,
            "sort_type": "time",
            "delete_type": "%",  # 删除类型
            "delete_size": 10,  # 删除数量/百分比
            "minCount": 0,  # 最小保留
            "monitorAble": True
        }

    @Slot(str, result=dict)
    def getDefault(self, path):
        return self.get_default(path)

    @Slot(QtCore.QJsonValue)
    def add_app(self, app: QtCore.QJsonValue):
        app = app.toVariant()
        self.log.debug("添加数据" + json.dumps(app, indent=4, ensure_ascii=False))
        app = self._normalize_monitor_item(app)
        drive = self._mountpoint_for_source(app["source"])
        # self.monitorData.append(app)
        if drive in self.monitorData:
            self.monitorData[drive]["monitor"].append(app)
        else:
            self.monitorData[drive] = {
                "threshold": 90,
                "monitor": [app]
            }
        self.set_config_change(True)

    @Slot(QtCore.QJsonValue)
    def addApp(self, app: QtCore.QJsonValue):
        self.add_app(app)

    @Slot(str, str, int)
    @Slot(str, str, float)
    @Slot(str, str, bool)
    @Slot(str, str, str)
    def changeValue(self, mountpoint, key, value):
        mountpoint = self._normalize_mountpoint(mountpoint)
        if mountpoint not in self.monitorData:
            self.monitorData[mountpoint] = {"threshold": 90, "monitor": []}
        if key == "threshold":
            value = max(0, min(100, try_get_int(value)))
        self.monitorData[mountpoint][key] = value
        self.set_config_change(self.monitorData != self.monitorData_old)

    @Slot(str, int, str, int)
    @Slot(str, int, str, float)
    @Slot(str, int, str, bool)
    @Slot(str, int, str, str)
    def changeMonitorValue(self, mountpoint, index, key, value):
        mountpoint = self._normalize_mountpoint(mountpoint)
        if mountpoint not in self.monitorData:
            return
        monitors = self.monitorData[mountpoint].get("monitor", [])
        if index < 0 or index >= len(monitors):
            return
        if key in ("delete_size", "minCount"):
            value = max(0, try_get_int(value))
        monitors[index][key] = value
        self.set_config_change(self.monitorData != self.monitorData_old)

    @Slot(str, int, result=dict)
    def index(self, mountpoint, index):
        mountpoint = self._normalize_mountpoint(mountpoint)
        monitors = self.monitorData.get(mountpoint, {}).get("monitor", [])
        if index < 0 or index >= len(monitors):
            return {}
        return monitors[index]

    @Slot(str, result=int)
    def getState_(self, mountpoint):
        mountpoint = self._normalize_mountpoint(mountpoint)
        disk_info = self.fullData.get(mountpoint)
        if not disk_info:
            return -2
        return 0 if disk_info["percentage"] > disk_info["threshold"] else 1
