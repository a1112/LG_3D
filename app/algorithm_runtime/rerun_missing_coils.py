"""
根据 SecondaryCoil / Coil 差异重新运行缺失钢卷的 3D 检测逻辑。

用法示例:
    python rerun_missing_coils.py --start-id 12711
"""

import faulthandler
import sys
from pathlib import Path

faulthandler.enable(all_threads=True)

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "Base"))

import argparse
import logging
import multiprocessing

from Base.utils.StdoutLog import Logger
from Base.utils.LoggerProcess import LoggerProcess
from SplicingService.ImageMosaicThread import ImageMosaicThread


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="根据 SecondaryCoil / Coil 差异重算缺失钢卷。")
    parser.add_argument(
        "--start-id",
        type=int,
        default=15000,
        help="起始 SecondaryCoil.Id (包含)，为空则从最大 Id 开始",
    )
    parser.add_argument(
        "--end-id",
        type=int,
        default=130000,
        help="结束 SecondaryCoil.Id (包含)，为空则遍历到最小 Id",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    try:
        from ultralytics.utils import LOGGER as ULTRA_LOGGER
        ULTRA_LOGGER.setLevel(logging.WARNING)
    except Exception:
        pass

    Logger("算法历史重算")
    logger_process = LoggerProcess(log_file="log/rerun_missing_coils.log")
    logger_process.start()

    try:
        queue: multiprocessing.Queue = multiprocessing.Queue()
        image_mosaic_thread = ImageMosaicThread(queue, logger_process)
        # 不启动线程, 直接在当前进程同步执行按差集重算逻辑
        image_mosaic_thread.run_missing_coils_by_diff(
            start_id=args.start_id,
            end_id=args.end_id,
        )
    finally:
        logger_process.stop()


if __name__ == "__main__":
    main()

