import asyncio
import json
from queue import Queue
from threading import Thread

from .api_core import app
from fastapi import WebSocket

import Globs

class ReceiveTextThread(Thread):
    def __init__(self, websocket):
        super().__init__()
        self.websocket = websocket
        self.queue = Queue()

    def run(self):
        while True:
            self.queue.put(self.websocket.receive())

    def hasMsg(self):
        return self.queue.qsize() > 0

    def get(self):
        return self.queue.get()

@app.websocket("/ws/reDetection")
async  def wsReDetectionTask(websocket: WebSocket):
    await websocket.accept()

    async def receive_messages():
        while True:
            print("Received start")
            data = await websocket.receive_text()  # 非阻塞的接收消息
            print(f"Received: {data}")
            data = json.loads(data)
            from_id=data["from_id"]
            to_id=data["to_id"]
            Globs.imageMosaicThread.setReDetectionByCoilId(from_id, to_id)

    async def send_messages():
        while True:
            msg = Globs.imageMosaicThread.getReDetectionMsg()
            await websocket.send_text(f"Message "+str(msg))  # 非阻塞的发送消息

    # 使用 asyncio.gather 来并发运行接收和发送任务

    await asyncio.gather(receive_messages(), send_messages())

@app.websocket("/ws/DetectionState")
async  def wsDetectionState(websocket: WebSocket):
    await websocket.accept()
    async def receive_messages():
        while True:
            print("Received start")
            data = await websocket.receive_text()  # 非阻塞的接收消息
            print(f"Received: {data}")
            data = json.loads(data)
            from_id=data["from_id"]
            to_id=data["to_id"]

    async def send_messages():
        while True:
            await websocket.send_text(f"Message "+str(""))  # 非阻塞的发送消息


    await asyncio.gather(receive_messages(), send_messages())