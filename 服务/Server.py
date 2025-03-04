"""
LG_3D
完整的服务
"""
from multiprocessing import Process, freeze_support
from threading import Thread
import uvicorn
from utils.StdoutLog import Logger

from CONFIG import serverConfigProperty
from api import app

Logger("服务")
# 参数服务
from api import ApiInfo

# 数据库服务
from api import ApiDataBase

# 控制服务
from api import ApiServerControl

# 3D 数据 服务
from api import ApiDataServer

# 图像服务
from api import ApiImageServer

# 备份服务
from api import ApiBackupServer

# 测试服务
from api import ApiTest

# 参数设置
from api import ApiSettings


# from api import ApiDocs


class ServerProcess(Thread):
    def __init__(self, port):
        super().__init__()
        self.port = port

    def run(self):
        uvicorn.run(app, host="0.0.0.0", port=self.port)


if __name__ == '__main__':
    freeze_support()
    print(f"server main start count {serverConfigProperty.server_count} base_point {serverConfigProperty.server_port}")
    server_llist = []
    for port_ in range(serverConfigProperty.server_count):
        server_llist.append(ServerProcess(serverConfigProperty.server_port + port_))
    for server in server_llist:
        server.start()
    for server in server_llist:
        server.join()
