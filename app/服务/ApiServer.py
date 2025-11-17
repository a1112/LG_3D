import os

import uvicorn
from CONFIG import serverConfigProperty

try:  # pragma: no cover - allow running as a script
    from .bootstrap import prepare_api_process  # type: ignore
except ImportError:  # pragma: no cover
    from bootstrap import prepare_api_process  # type: ignore

try:  # pragma: no cover - fallback when executed as a script
    from .api_app import create_app  # type: ignore
except ImportError:  # pragma: no cover
    from api_app import create_app  # type: ignore

prepare_api_process()


def create_api_app():
    app = create_app(enable_runtime=False)
    return app


def run():
    worker_num = 1 if os.name == "nt" else serverConfigProperty.server_count
    if worker_num != serverConfigProperty.server_count:
        print("Windows environment forces single worker to avoid multi-process issues")
    print(f"app:run  {serverConfigProperty.server_host}:{serverConfigProperty.server_port}")
    uvicorn.run(
        create_api_app,
        host=serverConfigProperty.server_host,
        port=serverConfigProperty.server_port,
        workers=worker_num,
        factory=True,
    )


if __name__ == "__main__":
    run()
