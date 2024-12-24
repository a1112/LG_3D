import socket
from pathlib import Path
import concurrent.futures

from alg import detection

save_base_folder=None
if "DESKTOP-V9D92AP" == socket.gethostname():
    save_base_folder = Path(fr"E:\detection_save")
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:

    for i in range(40000):
        print(i)
        result = executor.submit(detection.detection_by_coil_id, i,save_base_folder=save_base_folder)
