import os
from collections import defaultdict

from enum_types.enums import SoftRunStateEnum


class GlobSoftConfig:
    def __init__(self, parent=None):
        self.pid_map = defaultdict(set)

    def get_pip_list(self,exe):
        return list(self.pid_map[os.path.normpath(exe)])

    def set_soft_state(self,url,pp_id,state):
        if state==SoftRunStateEnum.RUNNING and pp_id > 42:
            self.pid_map[url].add(pp_id)
        else:
            self.pid_map[url].copy()

globSoftConfig = GlobSoftConfig()