from typing import Optional
import logging

from fastapi import APIRouter, HTTPException, WebSocket

from .alg_test_manager import alg_test_manager
from .api_core import app

logger = logging.getLogger(__name__)
router = APIRouter(tags=["算法测试"])


@router.get("/alg_2d/models")
def list_alg_models():
    """获取可用的算法模型列表"""
    logger.info("收到获取模型列表请求")
    try:
        models = alg_test_manager.list_models()
        logger.info(f"返回模型列表，共 {len(models)} 个模型: {[m.get('name') for m in models]}")
        if not models:
            logger.warning("模型列表为空，请将 .pt 或 .onnx 模型文件放置到 CONFIG_3D/model 目录")
        return {"models": models}
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
