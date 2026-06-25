import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "app" / "Server"))
sys.path.insert(0, str(PROJECT_ROOT / "package" / "CoilDataBase"))


def test_default_cache_backend_is_set_before_cache_import(monkeypatch):
    from runtime_settings import ensure_default_cache_backend

    monkeypatch.delenv("IMAGE_CACHE_BACKEND", raising=False)
    monkeypatch.delenv("CACHE_BACKEND", raising=False)

    ensure_default_cache_backend()

    assert os.environ["IMAGE_CACHE_BACKEND"] == "redis"


def test_explicit_cache_backend_is_not_overridden(monkeypatch):
    from runtime_settings import ensure_default_cache_backend

    monkeypatch.setenv("IMAGE_CACHE_BACKEND", "memory")

    ensure_default_cache_backend()

    assert os.environ["IMAGE_CACHE_BACKEND"] == "memory"


def test_api_workers_default_to_single_process_on_windows(monkeypatch):
    from runtime_settings import get_api_workers

    monkeypatch.delenv("API_WORKERS", raising=False)

    assert get_api_workers("win32") == 1


def test_api_workers_can_be_configured(monkeypatch):
    from runtime_settings import get_api_workers

    monkeypatch.setenv("API_WORKERS", "4")

    assert get_api_workers("linux") == 4


def test_db_pool_settings_are_environment_configurable(monkeypatch):
    from CoilDataBase.db_settings import sqlalchemy_pool_settings

    monkeypatch.setenv("DB_POOL_SIZE", "3")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "4")
    monkeypatch.setenv("DB_POOL_TIMEOUT", "5")
    monkeypatch.setenv("DB_POOL_RECYCLE", "6")

    assert sqlalchemy_pool_settings() == {
        "pool_size": 3,
        "max_overflow": 4,
        "pool_timeout": 5,
        "pool_recycle": 6,
        "pool_pre_ping": True,
        "echo": False,
    }


def test_database_url_env_overrides_config_url(monkeypatch):
    from CoilDataBase.config import Config, get_url

    database_url = "postgresql+psycopg://lg3d_app:secret@127.0.0.1:5432/Coil"
    monkeypatch.setenv("COIL_DATABASE_URL", database_url)
    monkeypatch.setattr(
        Config, "url",
        "mysql+pymysql://root:nercar@127.0.0.1:3306/Coil?charset=utf8")

    assert get_url() == database_url


def test_database_url_is_not_printed_to_stdout(monkeypatch, capsys):
    from CoilDataBase.config import get_url

    database_url = "postgresql+psycopg://lg3d_app:secret@127.0.0.1:5432/Coil"
    monkeypatch.setenv("COIL_DATABASE_URL", database_url)

    assert get_url() == database_url
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "secret" not in captured.err


def test_default_database_url_points_to_postgresql(monkeypatch):
    from sqlalchemy.engine import make_url

    from CoilDataBase.config import Config, get_url

    monkeypatch.delenv("COIL_DATABASE_URL", raising=False)
    monkeypatch.setattr(Config, "url", None)

    parsed = make_url(get_url())

    assert parsed.drivername == "postgresql+psycopg"
    assert parsed.host == "127.0.0.1"
    assert parsed.port == 5432
    assert parsed.database == "coil"


def test_postgresql_url_uses_sqlalchemy_builder_without_mysql_charset():
    from sqlalchemy.engine import make_url

    from CoilDataBase.config import DeriverList, build_url

    class PostgresConfig:
        deriver = DeriverList.postgresql
        user = "lg3d_app"
        password = "pa:ss@word"
        host = "127.0.0.1"
        port = 5432
        database = "Coil"
        charset = "utf8"
        file_url = ""

    parsed = make_url(build_url(PostgresConfig))

    assert parsed.drivername == "postgresql+psycopg"
    assert parsed.password == "pa:ss@word"
    assert parsed.query == {}


def test_mysql_url_keeps_charset_query():
    from sqlalchemy.engine import make_url

    from CoilDataBase.config import DeriverList, build_url

    class MysqlConfig:
        deriver = DeriverList.mysql
        user = "root"
        password = "nercar"
        host = "127.0.0.1"
        port = 3306
        database = "Coil"
        charset = "utf8"
        file_url = ""

    parsed = make_url(build_url(MysqlConfig))

    assert parsed.drivername == "mysql+pymysql"
    assert parsed.query["charset"] == "utf8"


def test_storage_policy_skips_logs_and_raw_line_data_by_default(monkeypatch):
    from CoilDataBase.storage_policy import should_store_model_name, should_store_point_raw_fields, should_store_raw_data

    monkeypatch.delenv("COIL_STORE_LOG_DATA", raising=False)
    monkeypatch.delenv("COIL_STORE_RAW_DATA", raising=False)
    monkeypatch.delenv("COIL_STORE_POINT_RAW_DATA", raising=False)
    monkeypatch.delenv("COIL_DATABASE_SKIP_MODELS", raising=False)

    assert not should_store_model_name("CapTrueLogItem")
    assert not should_store_model_name("ServerDetectionError")
    assert not should_store_model_name("LineData")
    assert should_store_model_name("PointData")
    assert not should_store_raw_data()
    assert not should_store_point_raw_fields()
