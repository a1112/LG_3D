from pathlib import Path
import logging
import sys
import platform

from fastapi import APIRouter

from Base import CONFIG
from Base import Init
from Base.CONFIG import serverConfigProperty, defectClassesProperty
from .api_core import app
from CoilDataBase.core import engine
from cache import get_cache_mode, get_cache_stats
from CoilDataBase.Coil import get_coil, list_data_keys, get_coil_list, get_grad_list
from CoilDataBase.tool import to_dict
from testdata_config import get_testdata_asset_dir

logger = logging.getLogger(__name__)


router = APIRouter(tags=["参数服务"])


@router.get("/info")
async def info():
    info_ = {
        "ErrorMap": Init.ErrorMap,
        "RendererList": serverConfigProperty.renderer_list,
        "ColorMaps": Init.ColorMaps,
        "SaveImageType": serverConfigProperty.save_image_type,
        "PreviewSize": Init.PreviewSize,
    }
    info_.update(serverConfigProperty.to_dict())
    return info_


@router.get("/runtime_info")
def runtime_info():
    """
    运行环境信息：Python 版本、缓存模式、CPU/GPU 型号等，
    以及当前 3D 服务的运行模式（本地 / 开发者模式）。
    """
    # CPU 信息
    try:
        cpu_model = platform.processor() or platform.machine() or ""
    except Exception:
        cpu_model = ""

    # GPU 信息（如安装了 torch 且支持 CUDA）
    gpu_models = []
    try:
        import torch  # type: ignore[import]

        if torch.cuda.is_available():
            for idx in range(torch.cuda.device_count()):
                gpu_models.append(torch.cuda.get_device_name(idx))
    except Exception:
        # 可选依赖，失败时忽略 GPU 信息
        pass

    return {
        "python_version": sys.version,
        "cache_mode": get_cache_mode(),
        "cache_stats": get_cache_stats(),
        "cpu_model": cpu_model,
        "gpus": gpu_models,
        # 3D 后台运行模式信息，供 QML / “系统信息” 显示
        "is_local": CONFIG.isLoc,
        "developer_mode": getattr(CONFIG, "developer_mode", False),
        "offline_mode": getattr(CONFIG, "offline_mode", False),
    }


def _get_grader_list_(num):
    data = to_dict(get_grad_list(num))
    for d in data:
        sc = d["childrenCoil"]
        if sc:
            d.update(sc[0])
            del d["childrenCoil"]
        d["Next"] = CONFIG.infoConfigProperty.get_next(d["Weight"])

    return data


@router.get("/grader_list")
def grader_list(count: int = 100):
    return _get_grader_list_(min(max(int(count), 1), 1000))


# @router.get("/defectClasses")
# async def get_defect_classes():
#     return defectClassesProperty.config


@router.get("/database_info")
def database_info():
    """
    获取数据库信息。
    """
    coil_last = None
    try:
        coil_last = to_dict(get_coil(1)[0])
    except Exception as e:
        logger.warning("failed to load last coil for database_info: %s", e)
    return {
        "url": engine.url,
        "echo": engine.echo,
        "coil_last": coil_last,
    }


@router.get("/coil_list_value_change_keys")
async def coil_list_value_change_keys():
    return list(list_data_keys.keys())


_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _file_has_testdata(path_str: str, kind: str, coil_id: int) -> bool:
    """
    在开发者模式 + 本地环境下，辅助检查 TestData/<coil_id> 是否存在对应数据。
    """
    if not (getattr(CONFIG, "developer_mode", False) and CONFIG.isLoc):
        return False

    base = get_testdata_asset_dir(path_str)
    if not base.exists():
        return False

    if kind == "3D":
        for name in ("3D.npz", "3D.npy"):
            if (base / name).exists():
                return True
        return False

    if kind == "MESH":
        return any((base / relative_path).exists() for relative_path in (
            Path("meshes") / "defaultobject_mesh.mesh",
            Path("3D.obj"),
            Path("meshes") / "defaultobject.obj",
        ))

    if kind == "JPG":
        # 灰度预期：GRAY.*
        for folder in ("jpg", "png"):
            for ext in (".jpg", ".jpeg", ".png"):
                if (base / folder / f"GRAY{ext}").exists():
                    return True
        return False

    if kind == "2D":
        # 面积图预期：AREA.*
        for folder in ("jpg", "png"):
            for ext in (".jpg", ".jpeg", ".png"):
                if (base / folder / f"AREA{ext}").exists():
                    return True
        return False

    if kind == "AREA_MASK":
        for folder in ("jpg", "png"):
            for ext in (".jpg", ".jpeg", ".png"):
                if (base / folder / f"AREA_MASK{ext}").exists():
                    return True
        return False

    return False


def file_has(path_str: str, kind: str, coil_id: int) -> bool:
    """
    标准存在性检查；在开发者模式下，自动兼容 TestData。
    """
    path = Path(path_str)
    if path.exists():
        return True
    return _file_has_testdata(path_str, kind, coil_id)


def _surface_data_has(surface_config, coil_id: int, fast: bool) -> dict:
    data = {
        "JPG": file_has(surface_config.get_file(coil_id, "GRAY"), "JPG", coil_id),
        "2D": file_has(surface_config.get_file(coil_id, "AREA"), "2D", coil_id),
        "AREA_MASK": file_has(surface_config.get_file(coil_id, "AREA_MASK"), "AREA_MASK", coil_id),
    }
    if fast:
        return data

    data.update({
        "3D": file_has(surface_config.get_3d_file(coil_id), "3D", coil_id),
        "MESH": file_has(surface_config.get_mesh_file(coil_id), "MESH", coil_id),
    })
    return data


@router.get("/data_has/{coil_id:int}")
def get_daa_has(coil_id: int, fast: bool = False):
    return {
        key: _surface_data_has(surface_config, coil_id, fast)
        for key, surface_config in serverConfigProperty.surfaceConfigPropertyDict.items()
    }


app.include_router(router)
