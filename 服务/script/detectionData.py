import concurrent.futures

from alg import detection

with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:

    for i in range(40000):
        result = executor.submit(detection.detection_by_coil_id, i)
