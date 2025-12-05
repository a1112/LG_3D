import asyncio
import json
from queue import Queue
from threading import Thread

from fastapi import APIRouter
from fastapi import WebSocket

import Globs
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
            Globs.imageMosaicThread.set_re_detection_by_coil_id(from_id, to_id)

    async def send_messages():
        while True:
            # 周期性推送重新识别进度
            await asyncio.sleep(1)
            msg = Globs.imageMosaicThread.get_re_detection_msg()
            await websocket.send_text(json.dumps(msg))  # 非阻塞的发送消息

    # 使用 asyncio.gather 来并发运行接收和发送任务

    await asyncio.gather(receive_messages(), send_messages())


@router.get("/reDetection/start/{from_id:int}/{to_id:int}")
async def http_re_detection_start(from_id: int, to_id: int):
    """
    通过 HTTP 启动重新识别任务，指定起止 SecondaryCoilId。
    """
    Globs.imageMosaicThread.set_re_detection_by_coil_id(from_id, to_id)
    return Globs.imageMosaicThread.get_re_detection_msg()


@router.get("/reDetection/status")
async def http_re_detection_status():
    """
    获取当前重新识别任务进度。
    """
    return Globs.imageMosaicThread.get_re_detection_msg()


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
