import os

from sqlalchemy.engine import make_url


def _positive_int_from_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(parsed, 1)


def _nonnegative_int_from_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(parsed, 0)


def sqlalchemy_pool_settings() -> dict:
    return {
        "pool_size": _positive_int_from_env("DB_POOL_SIZE", 10),
        "max_overflow": _positive_int_from_env("DB_MAX_OVERFLOW", 20),
        "pool_timeout": _positive_int_from_env("DB_POOL_TIMEOUT", 30),
        "pool_recycle": _positive_int_from_env("DB_POOL_RECYCLE", 3600),
        "pool_pre_ping": True,
        "echo": False,
    }


def sqlalchemy_connect_args(url: str) -> dict:
    """Return finite driver-level I/O timeouts for supported databases.

    SQLAlchemy's ``pool_timeout`` only bounds waiting for a pooled connection;
    it cannot interrupt a driver stuck while connecting or executing a query.
    These settings keep that lower layer finite while remaining configurable
    for installations with unusually long reports or migrations.
    """
    parsed_url = make_url(url)
    explicit_query = parsed_url.query
    backend = parsed_url.get_backend_name()
    driver = parsed_url.get_driver_name()
    connect_timeout = _positive_int_from_env("DB_CONNECT_TIMEOUT", 10)
    operation_timeout = _nonnegative_int_from_env("DB_OPERATION_TIMEOUT", 300)
    lock_timeout = _nonnegative_int_from_env("DB_LOCK_TIMEOUT", 30)

    if backend == "postgresql":
        options = []
        if operation_timeout:
            options.append(f"-c statement_timeout={operation_timeout * 1000}")
        if lock_timeout:
            options.append(f"-c lock_timeout={lock_timeout * 1000}")
        connect_args = {}
        if "connect_timeout" not in explicit_query:
            connect_args["connect_timeout"] = connect_timeout
        if options and "options" not in explicit_query:
            connect_args["options"] = " ".join(options)
        return connect_args

    if backend == "mysql" and driver == "pymysql":
        connect_args = {}
        if "connect_timeout" not in explicit_query:
            connect_args["connect_timeout"] = connect_timeout
        if operation_timeout:
            if "read_timeout" not in explicit_query:
                connect_args["read_timeout"] = operation_timeout
            if "write_timeout" not in explicit_query:
                connect_args["write_timeout"] = operation_timeout
        return connect_args

    if backend == "mssql" and driver == "pymssql":
        connect_args = {}
        if "login_timeout" not in explicit_query:
            connect_args["login_timeout"] = connect_timeout
        if operation_timeout and "timeout" not in explicit_query:
            connect_args["timeout"] = operation_timeout
        return connect_args

    if backend == "sqlite":
        if "timeout" in explicit_query:
            return {}
        return {"timeout": lock_timeout or operation_timeout or 30}

    return {}


def sqlalchemy_timeout_url(url: str):
    """Embed timeout arguments for helpers that create their own engines."""
    parsed_url = make_url(url)
    timeout_query = {
        key: str(value)
        for key, value in sqlalchemy_connect_args(url).items()
    }
    if not timeout_query:
        return parsed_url
    return parsed_url.update_query_dict(timeout_query)
