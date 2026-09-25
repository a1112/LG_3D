
import CONFIG
import threading

from Log import logger
import Global

def _normalize_serial(value):
    return str(value or "").strip()


def _device_info_map(harvester):
    result = {}
    for device in harvester.device_info_list:
        try:
            serial = _normalize_serial(device.serial_number)
        except Exception as e:
            logger.debug("read enumerated camera serial failed: %s", e)
            continue
        if serial:
            result[serial] = device
    return result


if Global.USE_3D:
    from harvesters.core import Harvester

    h = Harvester()
    _harvester_lock = threading.RLock()

    # 添加GenTL生产者（根据需要调整路径）
    h.add_file(CONFIG.capTureConfig.SICKGigEVisionTL)

    # 更新设备列表
    h.update()

    _device_info_by_serial = _device_info_map(h)

    logger.debug("扫描到相机数量: %s", len(h.device_info_list))
    for device in h.device_info_list:
        logger.debug("扫描到相机: %s", device.display_name)
        logger.debug("相机序列号: %s", device.serial_number)
        logger.debug("相机 model: %s", device.model)
        logger.debug("相机 tl_type: %s", device.tl_type)
        _device_info_by_serial[_normalize_serial(device.serial_number)] = device


def get_camera_by_sn(target_sn):
    with _harvester_lock:
        try:
            return h.create_image_acquirer(serial_number=target_sn)
        except Exception as e:
            if "no candidate" not in str(e).lower():
                raise
            device_info = _device_info_by_serial.get(
                _normalize_serial(target_sn))
            if device_info is None:
                available_serials = sorted(_device_info_by_serial)
                raise RuntimeError(
                    "sick camera was not enumerated before acquisition "
                    f"started: sn={target_sn} available={available_serials}"
                ) from e
            try:
                list_index = h.device_info_list.index(device_info)
            except ValueError:
                h.device_info_list.append(device_info)
                list_index = len(h.device_info_list) - 1
            logger.warning(
                "sick camera candidate lookup failed; retrying cached device index: sn=%s index=%s error=%s",
                target_sn,
                list_index,
                e,
            )
            # Harvester.update() invalidates and destroys every active
            # ImageAcquirer. Reuse the DeviceInfo captured at startup and
            # bypass the failing serial-number property lookup instead.
            return h.create_image_acquirer(list_index=list_index)
