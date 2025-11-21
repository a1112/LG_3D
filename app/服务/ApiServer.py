import os
import sys
from pathlib import Path

# Ensure shared Base modules (property/utils/CONFIG 等) are on import path
BASE_DIR = Path(__file__).resolve().parents[2] / "Base"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import uvicorn
from api_app import create_app
from Base.utils.StdoutLog import Logger


def create_api_app():
    # API 只提供接口，不启动 Lis/Zip 等算法后台服务
    app = create_app(enable_runtime=False)
    return app


def run():
    uvicorn.run(
        "api_app:create_app",
        host="0.0.0.0",
        port=5010,
        workers=5,
        factory=True,
    )


if __name__ == "__main__":
    run()
