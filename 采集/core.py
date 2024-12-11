from harvesters.core import Harvester
import CONFIG
from Log import logger
h = Harvester()

# 添加GenTL生产者（根据需要调整路径）
h.add_file(CONFIG.capTureConfig.SICKGigEVisionTL)

# 更新设备列表
h.update()

logger.debug(fr"扫描到相机数量: {len(h.device_info_list)}")
for device in h.device_info_list:
    logger.debug(f"扫描到相机: {device.display_name}")
    logger.debug(f"相机序列号: {device.serial_number}")
    logger.debug(f"相机 model: {device.model}")
    logger.debug(f"相机 tl_type: {device.tl_type}")


def get_camera_by_sn(target_sn):
    return h.create_image_acquirer(serial_number=target_sn)
