import os

from utils.StdoutLog import Logger

def prepare_api_process(enable_background_runtime: str = "0") -> None:
    """
    Apply process-wide settings for the API-only service.

    - Initialize stdout logging.
    - Disable algorithm/background runtime by default (can be overridden by env).
    """
    Logger("服务")
    os.environ["ENABLE_BACKGROUND_RUNTIME"] = os.getenv(
        "ENABLE_BACKGROUND_RUNTIME", enable_background_runtime
    )
