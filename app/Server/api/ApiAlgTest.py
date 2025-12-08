from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket

from .alg_test_manager import alg_test_manager
from .api_core import app

router = APIRouter(tags=["算法测试"])


@router.get("/alg_2d/models")
def list_alg_models():
    return {"models": alg_test_manager.list_models()}


@router.post("/alg_2d/test/start")
def start_alg_test(payload: dict):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload 必须是对象")
    return alg_test_manager.start_job(payload)


@router.post("/alg_2d/test/stop")
def stop_alg_test(payload: Optional[dict] = None):
    task_id = None
    if isinstance(payload, dict):
        task_id = payload.get("task_id")
    return alg_test_manager.stop_job(task_id)


@router.websocket("/ws/alg_2d/test/progress")
async def alg_test_progress(websocket: WebSocket):
    await alg_test_manager.handle_websocket(websocket)


app.include_router(router)
