import os
from collections import defaultdict

from lg3d_service_monitor.monitoring.enums import SoftRunStateEnum
from lg3d_service_monitor.platform.windows.processes import normalize_path


class GlobSoftConfig:
    def __init__(self, parent=None):
        self.pid_map = defaultdict(set)

    def get_pip_list(self,exe):
        return self.get_pid_list(exe)

    def get_pid_list(self, exe):
        return list(self.pid_map[normalize_path(exe)])

    def set_soft_state(self,url,pid,state):
        url = normalize_path(url)
        if state==SoftRunStateEnum.RUNNING and pid > 0:
            self.pid_map[url].add(pid)
        else:
            self.pid_map.pop(url, None)

globSoftConfig = GlobSoftConfig()
