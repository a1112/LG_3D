import asyncio
import json
from queue import Queue
from threading import Thread

from fastapi import WebSocket

import Globs

from fastapi import APIRouter
from .api_core import app

router = APIRouter(tags=["算法服务-与算法同步运行"])


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


@router.websocket("/ws/reDetection")
async def ws_re_detection_task(websocket: WebSocket):
    await websocket.accept()

    async def receive_messages():
        while True:
            print("Received start")
            data = await websocket.receive_text()  # 非阻塞的接收消息
            print(f"Received: {data}")
            data = json.loads(data)
            from_id = data["from_id"]
            to_id = data["to_id"]
            Globs.imageMosaicThread.setReDetectionByCoilId(from_id, to_id)

    async def send_messages():
        while True:
            msg = Globs.imageMosaicThread.getReDetectionMsg()
            await websocket.send_text(f"Message " + str(msg))  # 非阻塞的发送消息

    # 使用 asyncio.gather 来并发运行接收和发送任务

    await asyncio.gather(receive_messages(), send_messages())


@router.get("/getServerState")
async def get_server_state():
    return Globs.serverMsg.msgList


@router.websocket("/ws/DetectionState")
async def ws_detection_state(websocket: WebSocket):
    """
    获取检测状态
    Args:
        websocket:

    Returns:

    """
    await websocket.accept()

    async def receive_messages():
        while True:
            print("Received start")
            data = await websocket.receive_text()  # 非阻塞的接收消息
            print(f"Received: {data}")
            data = json.loads(data)
            from_id = data["from_id"]
            to_id = data["to_id"]

    async def send_messages():
        while True:
            await websocket.send_text(f"Message " + str(""))  # 非阻塞的发送消息

    await asyncio.gather(receive_messages(), send_messages())

app.include_router(router)