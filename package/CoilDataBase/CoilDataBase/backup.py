import logging
import os
import subprocess
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from .config import Config, get_url
from .core import Session
from .models import *

log = logging.getLogger(__name__)
DEFAULT_BACKUP_TIMEOUT = 3600.0
DEFAULT_SQLITE_BACKUP_BATCH_SIZE = 500


def _get_backup_timeout() -> float:
    raw_value = os.getenv("COIL_DATABASE_BACKUP_TIMEOUT", str(DEFAULT_BACKUP_TIMEOUT))
    try:
        return max(float(raw_value), 1.0)
    except ValueError:
        log.warning("invalid COIL_DATABASE_BACKUP_TIMEOUT=%s, use %s", raw_value, DEFAULT_BACKUP_TIMEOUT)
        return DEFAULT_BACKUP_TIMEOUT


def _get_sqlite_backup_batch_size() -> int:
    raw_value = os.getenv("COIL_DATABASE_SQLITE_BACKUP_BATCH_SIZE",
                          str(DEFAULT_SQLITE_BACKUP_BATCH_SIZE))
    try:
        return max(int(raw_value), 1)
    except ValueError:
        log.warning(
            "invalid COIL_DATABASE_SQLITE_BACKUP_BATCH_SIZE=%s, use %s",
            raw_value, DEFAULT_SQLITE_BACKUP_BATCH_SIZE)
        return DEFAULT_SQLITE_BACKUP_BATCH_SIZE


def _current_url():
    return make_url(get_url())


def get_mysqldump_cmd(save_file, mysqldump_exe="mysqldump"):
    url = _current_url()
    cmd = [
        mysqldump_exe,
        "-h",
        url.host or Config.host,
        "-P",
        str(url.port or Config.port),
        "-u",
        url.username or Config.user,
        f"--default-character-set={url.query.get('charset', Config.charset)}",
        url.database or Config.database,
    ]
    return cmd, Path(save_file)


def get_pg_dump_cmd(save_file, pg_dump_exe="pg_dump"):
    url = _current_url()
    cmd = [
        pg_dump_exe,
        "-h",
        url.host or Config.host,
        "-p",
        str(url.port or 5432),
        "-U",
        url.username or Config.user,
        "-d",
        url.database or Config.database,
        "-f",
        str(save_file),
    ]
    return cmd, Path(save_file)


def _run_dump(cmd, save_path, env):
    save_path.parent.mkdir(parents=True, exist_ok=True)
    timeout = _get_backup_timeout()
    try:
        executable = Path(cmd[0]).name.lower()
        if executable.startswith("mysqldump"):
            with save_path.open("w", encoding="utf-8") as output:
                subprocess.run(cmd, stdout=output, env=env, check=True, timeout=timeout)
        else:
            subprocess.run(cmd, env=env, check=True, timeout=timeout)
        log.info("database backup success: %s", save_path)
        return True
    except subprocess.TimeoutExpired:
        log.error("database backup timed out after %ss: %s", timeout, save_path)
        return False
    except (OSError, subprocess.CalledProcessError) as e:
        log.error("database backup failed: %s", e)
        return False


def backup_to_sql(save_file, mysqldump_exe="mysqldump", pg_dump_exe="pg_dump"):
    url = _current_url()
    env = os.environ.copy()
    backend = url.get_backend_name()
    if url.password:
        if backend == "postgresql":
            env["PGPASSWORD"] = url.password
        elif backend == "mysql":
            env["MYSQL_PWD"] = url.password

    if backend == "postgresql":
        cmd, save_path = get_pg_dump_cmd(save_file, pg_dump_exe=pg_dump_exe)
    else:
        cmd, save_path = get_mysqldump_cmd(save_file,
                                           mysqldump_exe=mysqldump_exe)
    return _run_dump(cmd, save_path, env)


def backup_mysql_db(host, user, password, db_name, backup_file):
    cmd = ["mysqldump", "-h", host, "-u", user, db_name]
    env = os.environ.copy()
    if password:
        env["MYSQL_PWD"] = password
    return _run_dump(cmd, Path(backup_file), env)


def backup_to_sqlite(save_file):
    sqlite_engine = create_engine('sqlite:///' + save_file, echo=False)
    sqlite_session = None
    try:
        Base.metadata.create_all(sqlite_engine)
        session_sqlite = sessionmaker(bind=sqlite_engine)
        sqlite_session = session_sqlite()
        batch_size = _get_sqlite_backup_batch_size()
        class_by_table_name = {
            mapper.local_table.name: mapper.class_
            for mapper in Base.registry.mappers
        }
        for table_name in Base.metadata.tables:
            with Session() as session:
                cls = class_by_table_name[table_name]
                for index, item in enumerate(
                        session.query(cls).yield_per(batch_size), start=1):
                    sqlite_session.merge(item)
                    if index % batch_size == 0:
                        sqlite_session.commit()
                        sqlite_session.expunge_all()
            sqlite_session.commit()
            sqlite_session.expunge_all()
        return True
    except Exception:
        if sqlite_session is not None:
            sqlite_session.rollback()
        raise
    finally:
        if sqlite_session is not None:
            sqlite_session.close()
        sqlite_engine.dispose()
