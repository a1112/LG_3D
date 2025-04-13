from pathlib import Path
from configs.JoinConfig import join_config

from JoinService.JoinWork import JoinWork


def main():
    JoinWork(join_config)
    start_coil = 0
    save_folder1 = join_config.surfaces.values()[0].save_folder


if __name__ == "__main__":
    main()
