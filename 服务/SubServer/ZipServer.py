import Globs
from CONFIG import isLoc
from Globs import control
from property.ServerConfigProperty import SurfaceConfigProperty
from utils.Zip import ZipAndDeletionCameraData





class ZipServer(control.ProcessClass):
    """
    对服务器单数据进行压缩
    """
    def __init__(self, manager_queue):
        super().__init__()
        self.managerQueue = manager_queue

    def run(self):
        if isLoc:
            print("本地环境不进行压缩")
            return
        print("数据压缩进程启动")
        zip_and_deletion_list = []
        for surface in Globs.serverConfigProperty.surfaceConfigPropertyDict.values():
            surface: SurfaceConfigProperty
            for folder in surface.folderList:
                zip_and_deletion_list.append(ZipAndDeletionCameraData(folder["source"], reserve_num=100))
        for item in zip_and_deletion_list:
            item.start()
        for item in zip_and_deletion_list:
            item.join()