from threading import Thread
from fastapi import FastAPI
import uvicorn
import DecodeData

app = FastAPI()


@app.get("/currentCoil")
async def read_root():
    return DecodeData.currentCoil


def thread():
    uvicorn.run(app, host="0.0.0.0", port=6005)


Thread(target=thread).start()
