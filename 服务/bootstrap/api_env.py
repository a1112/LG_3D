from utils.StdoutLog import Logger


def prepare_api_process() -> None:
    """
    Apply process-wide settings for the API-only service.

    - Initialize stdout logging.
    """
    Logger("服务")
