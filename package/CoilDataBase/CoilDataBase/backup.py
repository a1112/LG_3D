import subprocess

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .core import Session
from .config import Config
from .models import *
from . import models
import datetime


def get_mysqldump_cmd(save_file, mysqldump_exe="mysqldump"):
    return f'"{mysqldump_exe}"' + f" -u {Config.user} -p{Config.password} {Config.database} > " + f'"{save_file}"'


def backup_to_sql(save_file, mysqldump_exe="mysqldump"):
    mysqldump_cmd = get_mysqldump_cmd(save_file, mysqldump_exe)
    try:
        subprocess.run(mysqldump_cmd, shell=True, check=True)
        print(f"MySQL 数据库 备份成功！ {mysqldump_cmd}")
    except subprocess.CalledProcessError as e:
        print(f"备份失败: {e}")


def backup_mysql_db(host, user, password, db_name, backup_file):
    # 构建 mysqldump 命令
    cmd = "mysqldump -u root -pnercar Coil > d:/Coil.sql"
    # cmd = f"mysqldump -h {host} -u {user} -p{password} {db_name} > {backup_file}"

    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"MySQL 数据库 {db_name} 备份成功！")
    except subprocess.CalledProcessError as e:
        print(f"备份失败: {e}")


def backup_to_sqlite(save_file):
    sqlite_engine = create_engine('sqlite:///'+save_file, echo=False)
    Base.metadata.create_all(sqlite_engine)
    session_sqlite = sessionmaker(bind=sqlite_engine)
    sqlite_session = session_sqlite()
    for tabel_name in Base.metadata.tables:
        with Session() as session:
            cls=getattr(models,tabel_name)
            for item in session.query(cls):
                # sqlite_item = cls(**{
                #     k:v for k,v in item.__dict__.items()
                #     if not k.startswith("_")
                # })
                # sqlite_session.add(sqlite_item)
                sqlite_session.merge(item)

    # 提交事务
    sqlite_session.commit()
    # 关闭session
    sqlite_session.close()

