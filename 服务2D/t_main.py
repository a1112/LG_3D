import time
from pathlib import Path
from configs.JoinConfig import join_config

from JoinService.JoinWork import JoinWork


def main():
    jw = JoinWork(join_config)

    start_coil =  1700

    start_coil = int(start_coil)

    max_coil = join_config.get_max_coil()
    print(fr"start_coil {start_coil} max_coil {max_coil}")
    while True:
        can = join_config.can_(start_coil)
        if not can:
            print(fr"not can {start_coil}")
            if int(max_coil)<=start_coil:
                time.sleep(5)
                continue
        start_coil += 1
        print(f"coil_id: {start_coil}")
        jw.add_work(start_coil)
        jw.get()
        print(f"coil_id: {start_coil} 处理完成")
        # input()


if __name__ == "__main__":
    main()
