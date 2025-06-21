import time
from pathlib import Path


from JoinService.JoinWork import JoinWork
from configs import CONFIG
from configs.JoinConfig import JoinConfig


def main():
    join_config = JoinConfig(CONFIG.JOIN_CONFIG_FILE)
    jw = JoinWork(join_config)

    start_coil = join_config.get_last_coil()

    start_coil = int(start_coil)
    print(start_coil)
    max_coil = join_config.get_max_coil()
    while True:
        can = join_config.can_(start_coil)
        if ( not can ) and start_coil >= (max_coil-2) :
            time.sleep(5)
            max_coil = join_config.get_max_coil()
            print(fr"not can {start_coil}  max_coil {max_coil}")
            continue
        start_coil += 1
        print(f"coil_id: {start_coil}")
        jw.add_work(start_coil)
        jw.get()
        print(f"coil_id: {start_coil} 处理完成")



if __name__ == "__main__":
    main()
