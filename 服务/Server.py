"""
LG_3D
完整的服务
"""
from multiprocessing import Process
import uvicorn

import CONFIG
from api import app

# 数据库服务
from api import ApiDataBase

# 参数服务
from api import ApiServerControl

# 3D 数据 服务
from api import ApiDataServer

# 图像服务
from api import ApiImageServer

# 备份服务
from api import ApiBackupServer


class ServerProcess(Process):
    def __init__(self,port):
        super().__init__()
        self.port = port

    def run(self):
        uvicorn.run(app, host="0.0.0.0", port=self.port)


if __name__ == '__main__':
    for port_ in range(CONFIG.server_count):
        ServerProcess(CONFIG.server_port + port_).start()
