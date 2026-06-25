import concurrent.futures
import logging
import socket
from pathlib import Path

from tqdm import tqdm

logger = logging.getLogger(__name__)


def default_save_folder() -> Path:
    save_base_folder = Path("E:/detection_sub_image")
    if socket.gethostname() == "DESKTOP-V9D92AP":
        save_base_folder = Path("E:/detection_sub_image")
    return save_base_folder


def clip_data(start_coil_id: int = 71019, end_coil_id: int = 80000, max_workers: int = 10) -> None:
    from Base.alg import detection

    save_base_folder = default_save_folder()
    save_base_folder.mkdir(exist_ok=True, parents=True)
    logger.info("save clipped data to %s", save_base_folder)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(detection.clip_by_coil_id, i, save_base_folder=save_base_folder)
            for i in tqdm(range(start_coil_id, end_coil_id))
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    clip_data()
