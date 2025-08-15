import time
from JoinService.JoinWork import JoinWork
from configs import CONFIG
from configs.JoinConfig import JoinConfig
from utils.MultiprocessColorLogger import EnhancedMultiProcessLogger


def main():
    join_config = JoinConfig(CONFIG.JOIN_CONFIG_FILE)
    jw = JoinWork(join_config)
    loger = EnhancedMultiProcessLogger.get_logger()
    start_coil =  92838

    start_coil = int(start_coil)

    max_coil = join_config.get_max_coil()
    loger.debug(fr"start_coil {start_coil} max_coil {max_coil}")
    while True:
        can = join_config.can_(start_coil)
        if not can:
            loger.info(fr"not can {start_coil}")
            if int(max_coil) <= start_coil:
                time.sleep(10)
                max_coil = join_config.get_max_coil()
                continue
        start_coil += 1
        loger.info(f"coil_id: {start_coil}")
        jw.add_work(start_coil)
        jw.get()
        loger.info(f"coil_id: {start_coil} 处理完成")
        # input()


if __name__ == "__main__":
    main()
