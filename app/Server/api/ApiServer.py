import asyncio
import json
import logging

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


async def _run_websocket_tasks(*coroutines) -> None:
    """Run paired websocket loops and always cancel the surviving peer."""
    tasks = [asyncio.create_task(coroutine) for coroutine in coroutines]
    try:
        done, _pending = await asyncio.wait(tasks,
                                            return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            exception = task.exception()
            if exception is not None:
                raise exception
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


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
            try:
                payload = json.loads(data)
                if not isinstance(payload, dict):
                    raise ValueError("重检请求必须是 JSON 对象")
                from_id = payload.get("from_id")
                to_id = payload.get("to_id")
                if (type(from_id) is not int or type(to_id) is not int
                        or from_id <= 0 or to_id < from_id):
                    raise ValueError("重检卷号必须是正整数，且结束卷号不能小于起始卷号")
                await asyncio.to_thread(
                    image_mosaic_thread.set_re_detection_by_coil_id, from_id,
                    to_id)
            except ValueError as exc:
                logger.warning("re-detection request rejected: %s", exc)
                await websocket.send_json({"error": str(exc)})

    async def send_messages():
        while True:
            # 周期性推送重新识别进度
            await asyncio.sleep(1)
            msg = image_mosaic_thread.get_re_detection_msg()
            await websocket.send_text(json.dumps(msg))  # 非阻塞的发送消息

    # 使用 asyncio.gather 来并发运行接收和发送任务

    try:
        await _run_websocket_tasks(receive_messages(), send_messages())
    except WebSocketDisconnect:
        return


@router.get("/reDetection/start/{from_id:int}/{to_id:int}")
async def http_re_detection_start(from_id: int, to_id: int):
    """
    通过 HTTP 启动重新识别任务，指定起止 SecondaryCoilId。
    """
    image_mosaic_thread = _image_mosaic_thread()
    try:
        await asyncio.to_thread(
            image_mosaic_thread.set_re_detection_by_coil_id, from_id, to_id)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
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
            await asyncio.sleep(1)
            await websocket.send_text(json.dumps(Globs.serverMsg.msgList, ensure_ascii=False))

    try:
        await _run_websocket_tasks(receive_messages(), send_messages())
    except WebSocketDisconnect:
        return

app.include_router(router)
