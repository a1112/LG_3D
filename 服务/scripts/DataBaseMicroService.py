from utils.StdoutLog import Logger
Logger("DatabaseApi")
import CONFIG
import pymysql
import sqlalchemy

from api import ApiDataBase, app, ApiServerControl

from api import ApiDataServer,ApiImageServer,ApiBackupServer

import uvicorn

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=CONFIG.data_base_api_port)
