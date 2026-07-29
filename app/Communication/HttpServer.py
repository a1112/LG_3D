import logging
import os
import time
from threading import Event, Thread

import uvicorn
from fastapi import FastAPI

import DecodeData

app = FastAPI()
logger = logging.getLogger(__name__)


def _positive_float_env(name: str, default: float) -> float:
    try:
        return max(float(os.getenv(name, str(default))), 0.1)
    except ValueError:
        logger.warning("invalid %s, use default %s", name, default)
        return default


HTTP_RESTART_DELAY = _positive_float_env("LG3D_HTTP_RESTART_DELAY", 2.0)


@app.get("/currentCoil")
async def read_root():
    return DecodeData.currentCoil


def run_http_server() -> None:
    uvicorn.run(app, host="0.0.0.0", port=6005, log_config=None)


def supervise_http_server(stop_event: Event | None = None) -> None:
    while stop_event is None or not stop_event.is_set():
        try:
            run_http_server()
        except SystemExit as exc:
            logger.error("HTTP server exited: code=%s", exc.code)
        except Exception as exc:
            logger.exception("HTTP server exited with an error: %s", exc)
        if stop_event is not None and stop_event.is_set():
            return
        logger.warning("HTTP server stopped; restart in %.1fs",
                       HTTP_RESTART_DELAY)
        if stop_event is None:
            time.sleep(HTTP_RESTART_DELAY)
        else:
            stop_event.wait(HTTP_RESTART_DELAY)


def start_http_server(stop_event: Event | None = None) -> Thread:
    thread = Thread(target=supervise_http_server,
                    args=(stop_event, ),
                    daemon=True,
                    name="communication-http-supervisor")
    thread.start()
    return thread
