from pathlib import Path
import sys
import platform

from fastapi import APIRouter

import CONFIG
import Init
from CONFIG import serverConfigProperty, defectClassesProperty
from .api_core import app
from CoilDataBase.core import engine
from cache import get_cache_mode
from CoilDataBase.Coil import get_coil, list_data_keys, get_coil_list, get_grad_list
from CoilDataBase.tool import to_dict


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
async def runtime_info():
    """
    运行环境信息：Python 版本、缓存模式、CPU/GPU 型号等。
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
        "cpu_model": cpu_model,
        "gpus": gpu_models,
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
async def grader_list(count: int = 100):
    return _get_grader_list_(count)


# @router.get("/defectClasses")
# async def get_defect_classes():
#     return defectClassesProperty.config


@router.get("/database_info")
async def database_info():
    """
    获取数据库信息。
    """
    coil_last = None
    try:
        coil_last = to_dict(get_coil(1)[0])
    except BaseException as e:  # noqa: BLE001
        print(e)
    return {
        "url": engine.url,
        "echo": engine.echo,
        "coil_last": coil_last,
    }


@router.get("/coil_list_value_change_keys")
async def coil_list_value_change_keys():
    return list(list_data_keys.keys())


def file_has(f_):
    print(f_)
    return Path(f_).exists()


@router.get("/data_has/{coil_id:int}")
async def get_daa_has(coil_id: int):
    return {
        key: {
            "3D": file_has(surface_config.get_3d_file(coil_id)),
            "MESH": file_has(surface_config.get_mesh_file(coil_id)),
            "JPG": file_has(surface_config.get_file(coil_id, "GRAY")),
            "2D": file_has(surface_config.get_file(coil_id, "AREA")),
        }
        for key, surface_config in serverConfigProperty.surfaceConfigPropertyDict.items()
    }


app.include_router(router)

