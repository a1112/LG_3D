import time
import shutil
from pathlib import Path
from JoinService.JoinWork import JoinWork
from configs import CONFIG
from configs.JoinConfig import JoinConfig
from utils.MultiprocessColorLogger import EnhancedMultiProcessLogger


def main():
    join_config = JoinConfig(CONFIG.JOIN_CONFIG_FILE)
    for surface in join_config.surfaces.values():
        save_folder = Path(surface.save_folder)
        if not save_folder.exists():
            continue
        for coil_folder in save_folder.iterdir():
            if not coil_folder.is_dir():
                continue
            cache_dir = coil_folder / "cache"
            if cache_dir.exists():
                shutil.rmtree(cache_dir, ignore_errors=True)
    jw = JoinWork(join_config)
    loger = EnhancedMultiProcessLogger.get_logger()
    start_coil =  join_config.get_source_min_coil()

    start_coil = int(142567)

    max_coil = join_config.get_save_max_coil()
    loger.debug(fr"start_coil {start_coil} max_coil {max_coil}")
    while True:
        can = join_config.can_(start_coil)
        if not can:
            loger.info(fr"not can {start_coil}")
            if int(max_coil) <= start_coil:
                time.sleep(10)
                max_coil = join_config.get_save_max_coil()
                continue
        start_coil += 1
        loger.info(f"coil_id: {start_coil}")
        jw.add_work(start_coil)
        jw.get()
        loger.info(f"coil_id: {start_coil} 处理完成")


if __name__ == "__main__":
    main()
