import logging

import GPUtil
import psutil

logger = logging.getLogger(__name__)


def getHardwareInfo():
    return {
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disk": get_disk_info(),
        "gpu": get_gpu_info(),
    }


def get_cpu_info():
    cpu_usage = psutil.cpu_percent()
    return {
        "key": "CPU",
        "value": f"{cpu_usage}%",
        "msg": f"CPU 使用率: {cpu_usage}%",
        "level": 3 if cpu_usage > 90 else 2 if cpu_usage > 70 else 1,
    }


def get_memory_info():
    memory = psutil.virtual_memory()
    return {
        "key": "内存",
        "value": f"{memory.percent}%",
        "msg": f"内存使用率: {memory.percent}%, 可用内存: {memory.available / (1024 ** 2):.2f} MB",
        "level": 3 if memory.percent > 90 else 2 if memory.percent > 70 else 1,
    }


def get_disk_info():
    disk_info = []
    all_used = 0
    all_total = 0
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except OSError as exc:
            logger.debug("skip disk partition %s: %s", partition.mountpoint, exc)
            continue
        disk_info.append(
            f"分区: {partition.device}, "
            f"总大小: {usage.total / (1024 ** 3):.2f} GB, "
            f"已用: {usage.used / (1024 ** 3):.2f} GB, "
            f"可用: {usage.free / (1024 ** 3):.2f} GB, "
            f"使用率: {usage.percent}%"
        )
        all_used += usage.used
        all_total += usage.total
    percent = (all_used / all_total * 100) if all_total else 0
    return {
        "key": "硬盘",
        "value": f"{percent:.2f}%",
        "msg": "\n".join(disk_info),
        "level": 3 if percent > 90 else 2 if percent > 70 else 1,
    }


def get_gpu_info():
    gpus = GPUtil.getGPUs()
    if not gpus:
        return {
            "key": "显卡",
            "value": "0.0%",
            "msg": "未检测到 GPU",
            "level": 1,
        }

    gpu_info = [f"显卡: {gpu.name}, 使用率: {gpu.load * 100:.2f}%" for gpu in gpus]
    max_load = max(gpu.load for gpu in gpus)
    return {
        "key": "显卡",
        "value": f"{max_load * 100:.1f}%",
        "msg": "\n".join(gpu_info),
        "level": 3 if max_load > 0.9 else 2 if max_load > 0.7 else 1,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    logger.info("%s", getHardwareInfo())
