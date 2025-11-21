import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent/"Base"))
sys.path.append(str(Path(__file__).parent.parent/"algorithm_runtime"))


from fastapi import FastAPI
import uvicorn
from api import app as fastapi_app  # noqa: E402

from Base.utils.StdoutLog import Logger

Logger("Server")



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
        "ApiServer:create_app",
        host="0.0.0.0",
        port=5010,
        workers=3,
        factory=True,
    )

if __name__ == "__main__":
    run()
