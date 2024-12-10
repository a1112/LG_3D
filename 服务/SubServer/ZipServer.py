import Globs
from CONFIG import isLoc
from Globs import control
from property.ServerConfigProperty import SurfaceConfigProperty
from utils.Zip import ZipAndDeletion


class ZipServer(control.ProcessClass):
    def __init__(self, managerQueue):
        super().__init__()
        self.managerQueue = managerQueue

    def run(self):
        if isLoc:
            print("本地环境不进行压缩")
            return
        print("数据压缩进程启动")
        ZipAndDeletionList = []
        for surface in Globs.serverConfigProperty.surfaceConfigPropertyDict.values():
            surface: SurfaceConfigProperty
            for folder in surface.folderList:
                ZipAndDeletionList.append(ZipAndDeletion(folder["source"], reserve_num=100))
        for item in ZipAndDeletionList:
            item.start()
        for item in ZipAndDeletionList:
            item.join()
