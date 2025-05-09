import time
from pathlib import Path
from configs.JoinConfig import join_config

from JoinService.JoinWork import JoinWork


def main():
    jw = JoinWork(join_config)

    start_coil = join_config.get_last_coil()

    start_coil = int(start_coil)
    print(start_coil)

    while True:
        can = join_config.can_(start_coil)
        if not can:
            time.sleep(5)
            print(fr"not can {start_coil}")
            continue
        start_coil += 1
        print(f"coil_id: {start_coil}")
        jw.add_work(start_coil)
        jw.get()
        print(f"coil_id: {start_coil} 处理完成")



if __name__ == "__main__":
    main()
