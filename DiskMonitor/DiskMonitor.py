import time

import psutil
from PySide6.QtCore import Slot
from MonitorBase.MonitorBase import MonitorBase


class DiskMonitor(MonitorBase):
    def __init__(self, parent=None):
        logFolder = "logs/DiskMonitor"
        configF = "config/DiskMonitor.json"
        super().__init__(configF, logFolder, parent)
        self.fullData={}

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
                for monitor in self.monitorData[key]["monitor"]:
                    if key in self.fullData:
                        pass

            time.sleep(5)

    @Slot(str, result=list)
    def getDiskMonitorData(self,mountpoint):
        if mountpoint in self.monitorData:
            return self.monitorData[mountpoint]["monitor"]
        return []
