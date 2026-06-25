import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from Base import CONFIG
from .api_core import app

logger = logging.getLogger(__name__)

router = APIRouter(tags=["参数设置"])


@router.post("/setDefectDict")
async def set_defect_dict(data: dict):
    """
    设置缺陷字典
    """
    logger.info("set defect dict: keys=%s", len(data))
    CONFIG.defectClassesProperty.set_data(data)


# 测试模式相关API
class TestModeRequest(BaseModel):
    enabled: bool

def _test_mode_config_path() -> Path:
    return Path(CONFIG.base_config_folder) / "test_mode_config.json"

@router.get("/settings/test_mode")
async def get_test_mode():
    """获取测试模式状态"""
    try:
        test_mode_config_path = _test_mode_config_path()
        if test_mode_config_path.exists():
            with open(test_mode_config_path, 'r', encoding='utf-8') as f:
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
        test_mode_config_path = _test_mode_config_path()
        # 确保目录存在
        test_mode_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 读取现有配置
        config = {}
        if test_mode_config_path.exists():
            with open(test_mode_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        # 更新测试模式设置
        config["test_mode"] = request.enabled
        
        # 保存配置
        with open(test_mode_config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        CONFIG.set_developer_mode(request.enabled)
        
        return {"status": "success", "test_mode": request.enabled}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存测试模式配置失败: {str(e)}")

@router.get("/settings/test_mode_status")
async def get_test_mode_status():
    """获取详细的测试模式状态信息"""
    try:
        test_mode_config_path = _test_mode_config_path()
        config_file_exists = test_mode_config_path.exists()
        config_file_value = False
        
        if config_file_exists:
            with open(test_mode_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                config_file_value = config.get("test_mode", False)
        
        return {
            "config_file_exists": config_file_exists,
            "config_file_value": config_file_value,
            "developer_mode": getattr(CONFIG, 'developer_mode', False),
            "is_local": getattr(CONFIG, 'isLoc', False),
            "config_file_path": str(test_mode_config_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取测试模式状态失败: {str(e)}")


app.include_router(router)
