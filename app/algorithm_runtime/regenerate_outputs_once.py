from __future__ import annotations

import argparse
import logging
import multiprocessing
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "Base"))

from Base.CONFIG import serverConfigProperty
import Globs
from Base.property.Base import DataIntegration
from Base.utils.LoggerProcess import LoggerProcess
from Base.utils.StdoutLog import Logger
from CoilDataBase.core import Session
from CoilDataBase.models.SecondaryCoil import SecondaryCoil
from SplicingService.ImageMosaic import ImageMosaic


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenerate 3D output files for one SecondaryCoil.")
    parser.add_argument("coil_id", type=int)
    parser.add_argument("--surface", choices=["S", "L"], action="append")
    return parser.parse_args()


def wait_until_ready(mosaic: ImageMosaic, expected_folders: int, timeout_s: float = 60.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if mosaic.imageSaver is not None and mosaic.d3Saver is not None and len(mosaic.dataFolderList) == expected_folders:
            return
        time.sleep(0.2)
    raise TimeoutError(f"ImageMosaic {mosaic.key} is not ready")


def regenerate_surface(surface_config: dict, coil: SecondaryCoil, logger_process: LoggerProcess) -> dict:
    queue: multiprocessing.Queue = multiprocessing.Queue()
    print(f"[{surface_config['key']}] create ImageMosaic", flush=True)
    mosaic = ImageMosaic(surface_config, queue, logger_process)
    try:
        mosaic.save3D_data = False
        Globs.control.save_3d_obj = False
        print(f"[{mosaic.key}] wait ready", flush=True)
        wait_until_ready(mosaic, len(surface_config["folderList"]))
        print(f"[{mosaic.key}] load camera data", flush=True)
        data_integration = DataIntegration(
            str(coil.Id),
            mosaic.saveFolder,
            mosaic.direction,
            mosaic.key,
        )
        data_integration.currentSecondaryCoil = coil
        mosaic.__getAllData__(data_integration)
        print(f"[{mosaic.key}] stitching", flush=True)
        mosaic.__stitching__(data_integration)
        print(f"[{mosaic.key}] save files", flush=True)
        mosaic.sync_save(data_integration)
        output_dir = mosaic.saveFolder / str(coil.Id)
        print(f"[{mosaic.key}] saved {output_dir}", flush=True)
        return {
            "surface": mosaic.key,
            "output_dir": str(output_dir),
            "npz": str(output_dir / "3D.npz"),
            "gray": str(output_dir / "jpg" / "GRAY.jpg"),
            "jet": str(output_dir / "jpg" / "JET.jpg"),
            "preview_gray": str(output_dir / "preview" / "GRAY.jpg"),
            "preview_jet": str(output_dir / "preview" / "JET.jpg"),
        }
    finally:
        print(f"[{surface_config['key']}] stop ImageMosaic", flush=True)
        mosaic.stop()
        mosaic.join(timeout=5)


def main() -> int:
    args = parse_args()
    print(f"regenerate_outputs_once coil_id={args.coil_id} surface={args.surface}", flush=True)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    Logger("算法补图")
    logger_process = LoggerProcess(log_file="log/regenerate_outputs_once.log")
    logger_process.start()
    try:
        with Session() as session:
            coil = session.query(SecondaryCoil).filter(SecondaryCoil.Id == args.coil_id).first()
            if coil is None:
                print(f"SecondaryCoil {args.coil_id} not found", file=sys.stderr, flush=True)
                return 2
            session.expunge(coil)

        selected = set(args.surface or ["S", "L"])
        results = []
        for surface_config in serverConfigProperty.surface:
            if surface_config["key"] not in selected:
                continue
            results.append(regenerate_surface(surface_config, coil, logger_process))

        for result in results:
            print(result, flush=True)
        return 0
    finally:
        logger_process.stop()


if __name__ == "__main__":
    exit_code = main()
    os._exit(exit_code)
