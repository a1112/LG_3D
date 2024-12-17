from enum import Enum
from multiprocessing import current_process


class DeriverList(Enum):
    mysql = "mysql+pymysql"
    sqlserver = "mssql+pymssql"
    sqlite = "sqlite"


PortDict = {
    DeriverList.mysql: 3306,
    DeriverList.sqlserver: 1433,
}


class Config:
    deriver = DeriverList.mysql
    user = "root"
    password = "nercar"
    host = "127.0.0.1"
    port = PortDict[DeriverList.mysql]
    database = "Coil"
    charset = "utf8"
    file_url=""


def get_url(config=Config):
    if Config.deriver in [DeriverList.sqlite]:
        url="{}:///{}".format(
        config.deriver.value,config.file_url
    )
    else:
        url= "{}://{}:{}@{}:{}/{}?charset={}".format(
            config.deriver.value, config.user, config.password, config.host, config.port, config.database, config.charset
        )
    if current_process().name == "MainProcess":
        print(url)
    return url
