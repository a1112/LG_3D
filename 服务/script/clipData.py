import socket
from pathlib import Path
import concurrent.futures

from alg import detection

save_base_folder = Path(fr"E:\detection_sub_image")
if "DESKTOP-V9D92AP" == socket.gethostname():
    save_base_folder = Path(fr"E:\detection_sub_image")
    save_base_folder.mkdir(exist_ok=True,parents=True)

for i in range(40000):
    result = detection.clip_by_coil_id(i,save_base_folder=save_base_folder)

# with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
#
#     for i in range(40000):
#         print(i)
#         result = executor.submit(detection.clip_by_coil_id, i,save_base_folder=save_base_folder)
#         print(result)