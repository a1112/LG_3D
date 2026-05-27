import os


def ensure_default_cache_backend() -> None:
    """Set the API cache backend before importing modules that initialize cache singletons."""
    if not os.getenv("IMAGE_CACHE_BACKEND") and not os.getenv("CACHE_BACKEND"):
        os.environ["IMAGE_CACHE_BACKEND"] = "redis"


def _positive_int_from_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(parsed, 1)


def get_api_workers(platform: str) -> int:
    default_workers = 1
    return _positive_int_from_env("API_WORKERS", default_workers)
