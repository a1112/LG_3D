from enum import Enum


class DeriverList(Enum):
    mysql = "mysql+pymysql"
    sqlserver = "mssql+pymssql"
    sqlite = "sqlite:///"


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


def get_url(config=Config):
    return "{}://{}:{}@{}:{}/{}?charset={}".format(
        config.deriver, config.user, config.password, config.host, config.port, config.database, config.charset
    )
