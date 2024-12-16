"""
LG_3D
完整的服务
"""
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


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=CONFIG.data_base_api_port)