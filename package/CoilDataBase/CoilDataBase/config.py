import logging
import os
from enum import Enum
from multiprocessing import current_process

from sqlalchemy.engine import URL, make_url

DATABASE_URL_ENV = "COIL_DATABASE_URL"
log = logging.getLogger(__name__)


class DeriverList(Enum):
    mysql = "mysql+pymysql"
    postgresql = "postgresql+psycopg"
    sqlserver = "mssql+pymssql"
    sqlite = "sqlite"


PortDict = {
    DeriverList.mysql: 3306,
    DeriverList.postgresql: 5432,
    DeriverList.sqlserver: 1433,
}


class Config:
    url = None
    deriver = DeriverList.postgresql
    user = "lg3d_app"
    password = "nercar"
    host = "127.0.0.1"
    port = PortDict[DeriverList.postgresql]
    database = "coil"
    charset = ""
    file_url = ""


def build_url(config=Config) -> str:
    if config.deriver in [DeriverList.sqlite]:
        url = URL.create(config.deriver.value, database=config.file_url)
    else:
        query = {}
        if config.deriver in [DeriverList.mysql] and config.charset:
            query["charset"] = config.charset
        url = URL.create(
            drivername=config.deriver.value,
            username=config.user,
            password=config.password,
            host=config.host,
            port=config.port,
            database=config.database,
            query=query,
        )
    return url.render_as_string(hide_password=False)


def get_url(config=Config) -> str:
    url = os.getenv(DATABASE_URL_ENV)
    if not url and config.url is not None:
        url = config.url
    if not url:
        url = build_url(config)
    if current_process().name == "MainProcess":
        try:
            safe_url = make_url(url).render_as_string(hide_password=True)
        except Exception:
            safe_url = "<invalid database url>"
        log.debug("database url: %s", safe_url)
    return url
