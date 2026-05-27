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
