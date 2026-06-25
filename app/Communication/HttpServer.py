from threading import Thread

import uvicorn
from fastapi import FastAPI

import DecodeData

app = FastAPI()


@app.get("/currentCoil")
async def read_root():
    return DecodeData.currentCoil


def run_http_server() -> None:
    uvicorn.run(app, host="0.0.0.0", port=6005)


def start_http_server() -> Thread:
    thread = Thread(target=run_http_server, daemon=True)
    thread.start()
    return thread
