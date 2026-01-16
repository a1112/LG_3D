import asyncio
import json
from pathlib import Path
from queue import Queue
from threading import Thread

from CoilDataBase.Coil import get_coil_status_by_coil_id

from fastapi import APIRouter, HTTPException
from fastapi import WebSocket
from pydantic import BaseModel

from Base import CONFIG
from .api_core import app

router = APIRouter(tags=["参数设置"])


@router.post("/setDefectDict")
async def set_defect_dict(data: dict):
    """
    设置缺陷字典
    """
    print(data)
    CONFIG.defectClassesProperty.set_data(data)


# 测试模式相关API
class TestModeRequest(BaseModel):
    enabled: bool

# 测试模式配置文件路径（不跟踪）
TEST_MODE_CONFIG_PATH = Path("CONFIG_3D/test_mode_config.json")

@router.get("/settings/test_mode")
async def get_test_mode():
    """获取测试模式状态"""
    try:
        if TEST_MODE_CONFIG_PATH.exists():
            with open(TEST_MODE_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return {"test_mode": config.get("test_mode", False)}
        else:
            # 如果文件不存在，返回CONFIG中的默认值
            return {"test_mode": getattr(CONFIG, 'developer_mode', False)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取测试模式配置失败: {str(e)}")

@router.post("/settings/test_mode")
async def set_test_mode(request: TestModeRequest):
    """设置测试模式状态"""
    try:
        # 确保目录存在
        TEST_MODE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # 读取现有配置
        config = {}
        if TEST_MODE_CONFIG_PATH.exists():
            with open(TEST_MODE_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        # 更新测试模式设置
        config["test_mode"] = request.enabled
        
        # 保存配置
        with open(TEST_MODE_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        # 同时更新CONFIG中的developer_mode（运行时生效）
        CONFIG.developer_mode = request.enabled
        CONFIG.isLoc = request.enabled  # 同步更新兼容变量
        
        return {"status": "success", "test_mode": request.enabled}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存测试模式配置失败: {str(e)}")

@router.get("/settings/test_mode_status")
async def get_test_mode_status():
    """获取详细的测试模式状态信息"""
    try:
        config_file_exists = TEST_MODE_CONFIG_PATH.exists()
        config_file_value = False
        
        if config_file_exists:
            with open(TEST_MODE_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                config_file_value = config.get("test_mode", False)
        
        return {
            "config_file_exists": config_file_exists,
            "config_file_value": config_file_value,
            "developer_mode": getattr(CONFIG, 'developer_mode', False),
            "is_local": getattr(CONFIG, 'isLoc', False),
            "config_file_path": str(TEST_MODE_CONFIG_PATH)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取测试模式状态失败: {str(e)}")


app.include_router(router)
