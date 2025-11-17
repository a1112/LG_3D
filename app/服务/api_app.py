import logging
from fastapi import FastAPI
import uvicorn

from CONFIG import server_api_port
from utils.StdoutLog import Logger
from runtime import runtime_controller

Logger("算法")

from api import app as fastapi_app  # noqa: E402


def _load_default_routers():
    from api import ApiInfo  # noqa: F401
    from api import ApiDataBase  # noqa: F401
    from api import ApiServerControl  # noqa: F401
    from api import ApiDataServer  # noqa: F401
    from api import ApiImageServer  # noqa: F401
    from api import ApiBackupServer  # noqa: F401
    from api import ApiTest  # noqa: F401
    from api import ApiSettings  # noqa: F401
    from AlarmDetection.Server import ApiAlarmInfo  # noqa: F401


def create_app(enable_runtime: bool = True) -> FastAPI:
    _load_default_routers()
    fastapi_app.state.enable_runtime = enable_runtime
    return fastapi_app


def run():
    uvicorn.run(
        lambda: create_app(enable_runtime=True),
        host="0.0.0.0",
        port=server_api_port,
        factory=True,
    )


if __name__ == "__main__":
    run()
