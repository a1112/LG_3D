import socket
from pathlib import Path
import concurrent.futures

from alg import detection
from alg.CoilMaskModel import CoilDetectionModel

# cdm = CoilDetectionModel(base_name="CoilDetection_ZD.pt")
save_base_folder = Path(fr"E:\detection_save_ZD__")
if "DESKTOP-V9D92AP" == socket.gethostname():
    save_base_folder = Path(fr"E:\detection_save__")
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    for i in range(39298,39300):
        detection.detection_by_coil_id(i, save_base_folder=save_base_folder)
        result = executor.submit(detection.detection_by_coil_id, i, save_base_folder=save_base_folder)
