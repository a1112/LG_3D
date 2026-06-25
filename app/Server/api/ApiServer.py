import asyncio
import json
import logging
from queue import Queue
from threading import Thread

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

import Globs
from .api_core import app

logger = logging.getLogger(__name__)

router = APIRouter(tags=["算法服务-与算法同步运行"])


def _runtime_available() -> bool:
    return getattr(app.state, "enable_runtime", True)


def _image_mosaic_thread():
    if not _runtime_available():
        raise HTTPException(status_code=503, detail="algorithm runtime routes are disabled")
    image_mosaic_thread = getattr(Globs, "imageMosaicThread", None)
    if image_mosaic_thread is None:
        raise HTTPException(status_code=503, detail="algorithm runtime is not attached to this process")
    return image_mosaic_thread


async def _close_unavailable_websocket(websocket: WebSocket, detail: str) -> None:
    await websocket.accept()
    await websocket.send_json({"error": detail})
    await websocket.close(code=1011)


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
    if not _runtime_available() or getattr(Globs, "imageMosaicThread", None) is None:
        await _close_unavailable_websocket(websocket, "algorithm runtime is not attached to this process")
        return

    await websocket.accept()
    image_mosaic_thread = _image_mosaic_thread()

    async def receive_messages():
        while True:
            data = await websocket.receive_text()  # 非阻塞的接收消息
            logger.debug("websocket received: %s", data)
            data = json.loads(data)
            from_id = data["from_id"]
            to_id = data["to_id"]
            image_mosaic_thread.set_re_detection_by_coil_id(from_id, to_id)

    async def send_messages():
        while True:
            # 周期性推送重新识别进度
            await asyncio.sleep(1)
            msg = image_mosaic_thread.get_re_detection_msg()
            await websocket.send_text(json.dumps(msg))  # 非阻塞的发送消息

    # 使用 asyncio.gather 来并发运行接收和发送任务

    await asyncio.gather(receive_messages(), send_messages())


@router.get("/reDetection/start/{from_id:int}/{to_id:int}")
async def http_re_detection_start(from_id: int, to_id: int):
    """
    通过 HTTP 启动重新识别任务，指定起止 SecondaryCoilId。
    """
    image_mosaic_thread = _image_mosaic_thread()
    image_mosaic_thread.set_re_detection_by_coil_id(from_id, to_id)
    return image_mosaic_thread.get_re_detection_msg()


@router.get("/reDetection/status")
async def http_re_detection_status():
    """
    获取当前重新识别任务进度。
    """
    return _image_mosaic_thread().get_re_detection_msg()


@router.get("/getServerState")
async def get_server_state():
    if not _runtime_available():
        raise HTTPException(status_code=503, detail="algorithm runtime routes are disabled")
    return Globs.serverMsg.msgList


@router.websocket("/ws/DetectionState")
async def ws_detection_state(websocket: WebSocket):
    """
    获取检测状态
    Args:
        websocket:

    Returns:

    """
    if not _runtime_available():
        await _close_unavailable_websocket(websocket, "algorithm runtime routes are disabled")
        return

    await websocket.accept()

    async def receive_messages():
        while True:
            data = await websocket.receive_text()  # 非阻塞的接收消息
            logger.debug("websocket received: %s", data)
            data = json.loads(data)
            from_id = data["from_id"]
            to_id = data["to_id"]

    async def send_messages():
        while True:
            await websocket.send_text(f"Message " + str(""))  # 非阻塞的发送消息

    try:
        await asyncio.gather(receive_messages(), send_messages())
    except WebSocketDisconnect:
        return

app.include_router(router)
