"""
LG_3D
完整的服务
"""
from multiprocessing import Process, freeze_support
import uvicorn
from utils.StdoutLog import Logger

Logger("服务")
from Globs import serverConfigProperty
from api import app

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


class ServerProcess(Process):
    def __init__(self, port):
        super().__init__()
        self.port = port

    def run(self):
        uvicorn.run(app, host="0.0.0.0", port=self.port)


if __name__ == '__main__':
    freeze_support()
    for port_ in range(serverConfigProperty.server_count):
        ServerProcess(serverConfigProperty.server_port + port_).start()
