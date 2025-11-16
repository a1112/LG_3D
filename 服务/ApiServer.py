import os

import uvicorn
from CONFIG import serverConfigProperty

try:  # pragma: no cover - allow running as a script
    from .bootstrap import prepare_api_process  # type: ignore
except ImportError:  # pragma: no cover
    from bootstrap import prepare_api_process  # type: ignore

try:  # pragma: no cover - fallback when executed as a script
    from .main import create_app  # type: ignore
except ImportError:  # pragma: no cover
    from main import create_app  # type: ignore

# Only process-level bootstrap lives outside of FastAPI/uvicorn concerns.
prepare_api_process()


def run():
    worker_num = 1 if os.name == "nt" else serverConfigProperty.server_count
    if worker_num != serverConfigProperty.server_count:
        print("Windows 环境下强制使用单 worker 避免多进程异常")
    print(fr"app:run  {serverConfigProperty.server_host}:{serverConfigProperty.server_port}" )
    uvicorn.run(
        create_app,
        host=serverConfigProperty.server_host,
        port=serverConfigProperty.server_port,
        workers=worker_num,
        factory=True,
    )


if __name__ == "__main__":
    run()
