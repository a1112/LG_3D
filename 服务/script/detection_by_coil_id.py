import socket
from pathlib import Path
import concurrent.futures
# 根据ID 检测
from sqlalchemy.util import await_only

import Globs
from alg import detection
from alg.CoilMaskModel import CoilDetectionModel

# cdm = CoilDetectionModel(base_name="CoilDetection_ZD.pt")
save_base_folder = Path(fr"E:\detection_save_ZD")
if "DESKTOP-V9D92AP" == socket.gethostname():
    save_base_folder = Path(fr"E:\detection_save")
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    for i in range(30000, 45551):
        result = executor.submit(detection.detection_by_coil_id, i, save_base_folder=save_base_folder,save_only=True)
        # result = result.result()
        # print(result)