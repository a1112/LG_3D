import logging
import os
import time
from pathlib import Path
from threading import Thread

import psutil

from CoilDataBase.Coil import get_secondary_coil

logger = logging.getLogger(__name__)


def kill_process_(p):
    if p is None:
        return False
    try:
        for proc in p.children(recursive=True):
            proc.kill()
        p.kill()
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        logger.warning("kill process failed: %s", e)
        return False

def get_proc(name):
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == name:
            return proc
    return None

def kill_process(name):
    proc = get_proc(name)
    if proc is None:
        logger.debug("process %s is not running", name)
        return
    try:
        if kill_process_(proc):
            logger.info("terminated process %s", name)
    except psutil.AccessDenied:
        logger.warning("access denied while terminating process %s", name)
    except Exception as e:
        logger.exception("terminate process %s failed: %s", name, e)

def get_folder_last_by_folder(folder):
    last_id= 0
    folder = Path(folder)
    if not folder.exists():
        logger.debug("capture folder does not exist: %s", folder)
        return last_id
    for f in folder.iterdir():
        try:
            if int(f.stem) > last_id:

                last_id = int(f.stem)
        except ValueError:
            continue
    return last_id

def get_folder_last_id_3d():
    return  min(
        get_folder_last_by_folder(fr"G:\Cap_S_U"),
        get_folder_last_by_folder(fr"G:\Cap_S_M"),
        get_folder_last_by_folder(fr"G:\Cap_S_D"),
        get_folder_last_by_folder(fr"F:\Cap_L_U"),
        get_folder_last_by_folder(fr"F:\Cap_L_M"),
        get_folder_last_by_folder(fr"F:\Cap_L_D"),
    )
def has_3D_files(folder):
    return (folder/"3d").exists()

def has_3D_datas(coil_id):
    return [
        has_3D_files(Path(fr"G:\Cap_S_U")/str(coil_id)),
        has_3D_files(Path(fr"G:\Cap_S_M")/str(coil_id)),
        has_3D_files(Path(fr"G:\Cap_S_D")/str(coil_id)),
        has_3D_files(Path(fr"F:\Cap_L_U")/str(coil_id)),
        has_3D_files(Path(fr"F:\Cap_L_M")/str(coil_id)),
        has_3D_files(Path(fr"F:\Cap_L_D")/str(coil_id)),
    ]


def has_2D_files(folder):
    return (folder/"area").exists()


def has_2D_datas(coil_id):
    return [
        has_2D_files(Path(fr"G:\Cap_S_U") / str(coil_id)),
        has_2D_files(Path(fr"G:\Cap_S_M") / str(coil_id)),
        has_2D_files(Path(fr"G:\Cap_S_D") / str(coil_id)),
        has_2D_files(Path(fr"F:\Cap_L_U") / str(coil_id)),
        has_2D_files(Path(fr"F:\Cap_L_M") / str(coil_id)),
        has_2D_files(Path(fr"F:\Cap_L_D") / str(coil_id)),
    ]


class ThreadLis(Thread):
    def __init__(self):
        Thread.__init__(self, daemon=True)
        self.start()

    def get_last_id(self):
        last_secondary = get_secondary_coil(1)[0]
        scan_id = last_secondary.Id
        return scan_id

    def run(self):
        scan_id = 0
        step=0
        while True:
            try:
                scan_id = self.get_last_id()
                time.sleep(20)
                if not all(has_3D_datas(scan_id-1)):
                    kill_process("CapTure.exe")
                    time.sleep(600)
                if not all(has_2D_datas(scan_id-1)):
                    kill_process("Cap2d.exe")
                    time.sleep(600)
            except Exception as e:
                logger.exception("ThreadLis check failed: %s", e)
                time.sleep(5)

class ThreadLis2D(Thread):
    pass

ThreadLis()
