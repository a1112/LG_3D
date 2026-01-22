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
    from api import ApiAlgTest  # noqa: F401


def create_app(enable_runtime: bool = True) -> FastAPI:
    _load_default_routers()
    fastapi_app.state.enable_runtime = enable_runtime
    return fastapi_app


def run():
    import os
    # 使用 Redis 缓存以支持多进程
    os.environ["IMAGE_CACHE_BACKEND"] = "redis"
    # Redis 配置（可选，使用默认值：localhost:6379 db=0）
    # os.environ["CACHE_REDIS_HOST"] = "localhost"
    # os.environ["CACHE_REDIS_PORT"] = "6379"
    # os.environ["CACHE_REDIS_DB"] = "0"

    uvicorn.run(
        "Server:create_app",
        host="0.0.0.0",
        port=5010,
        workers=5,  # Redis 缓存支持多进程
        factory=True,
    )

if __name__ == "__main__":
    run()
