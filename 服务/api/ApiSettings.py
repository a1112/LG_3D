import asyncio
import json
from queue import Queue
from threading import Thread

from fastapi import APIRouter
from fastapi import WebSocket

import CONFIG
import Globs
from .api_core import app

router = APIRouter(tags=["参数设置"])


@router.post("/setDefectDict")
async def set_defect_dict(data: dict):
    """
    设置缺陷字典
    """
    print(data)
    CONFIG.defectClassesProperty.set_data(data)


app.include_router(router)
