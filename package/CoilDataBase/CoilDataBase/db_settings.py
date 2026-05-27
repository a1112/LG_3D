import os


def _positive_int_from_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(parsed, 1)


def sqlalchemy_pool_settings() -> dict:
    return {
        "pool_size": _positive_int_from_env("DB_POOL_SIZE", 10),
        "max_overflow": _positive_int_from_env("DB_MAX_OVERFLOW", 20),
        "pool_timeout": _positive_int_from_env("DB_POOL_TIMEOUT", 30),
        "pool_recycle": _positive_int_from_env("DB_POOL_RECYCLE", 3600),
        "pool_pre_ping": True,
        "echo": False,
    }
