import socket
from pathlib import Path
import concurrent.futures

from alg import detection

save_base_folder = Path(fr"E:\detection_sub_image_折叠")
if "DESKTOP-V9D92AP" == socket.gethostname():
    save_base_folder = Path(fr"E:\detection_sub_image_折叠")
    save_base_folder.mkdir(exist_ok=True, parents=True)

# for i in range(40000):
#     result = detection.clip_by_coil_id(i,save_base_folder=save_base_folder)

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    for i in [35550, 36857, 34074, 9843]:
        result = executor.submit(detection.clip_by_coil_id, i, save_base_folder=save_base_folder)

#  4V10014000 35550   36857  34074 9843
