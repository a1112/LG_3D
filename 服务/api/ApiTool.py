from pathlib import Path
from alg import detection
from fastapi import UploadFile, File, APIRouter

from .api_core import app

import Globs

router = APIRouter(tags=["工具服务"])

@router.get("/clipMaxImage/{coil_id:int}/{key:str}")
async def clip_max_image(coil_id, key, save_url = None):
    """
    切割图像，保持到存储位置
    :param coil_id: id
    :param key: 表面关键字
    :param save_url: 保持路径
    :return:
    """
    if save_url is None:
        save_url=Globs.serverConfigProperty.get_folder(coil_id, key)
    save_url = Path(save_url)
    save_url=save_url/"clip_max"
    if save_url.exists():
        return
    save_url.mkdir(parents=True, exist_ok=True)
    return detection.clip_by_coil_id(coil_id, save_url, key)


app.include_router(router)