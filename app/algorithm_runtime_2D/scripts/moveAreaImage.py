import logging
import shutil

from tqdm import tqdm

from configs import CONFIG
from configs.JoinConfig import JoinConfig

logger = logging.getLogger(__name__)


def move_recent_area_images(window_size: int = 20000) -> None:
    join_config = JoinConfig(CONFIG.JOIN_CONFIG_FILE)
    max_coil = join_config.get_max_coil()
    logger.info("max coil id: %s", max_coil)

    start_coil_id = max_coil - window_size
    for i in tqdm(range(start_coil_id, max_coil)):
        for surface_config in join_config.surfaces.values():
            url = surface_config.get_area_url(i)
            move_to_folder = surface_config.area_copy_to_folder / str(i)

            if url.exists():
                move_to_folder.mkdir(parents=True, exist_ok=True)
                shutil.copy(url, move_to_folder)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    move_recent_area_images()
