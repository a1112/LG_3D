import os
import time
from pathlib import Path
from threading import Thread
from CoilDataBase.Coil import get_secondary_coil

import psutil

def kill_process(p):
    try:
        for proc in p.children():
            proc.kill()
        p.kill()
    except:
        pass

def get_proc(name):
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == name:
            return proc
    return None

def kill_process(name):
    try:
        kill_process(get_proc(name))
        print(f"成功终止 {name}")
    except psutil.AccessDenied:
        print(f"权限不足，无法终止 {name}")
    except Exception as e:
        print(f"终止进程时出错: {e}")

def get_folder_last_by_folder(folder):
    last_id= 0
    for f in Path(folder).iterdir():
        try:
            if int(f.stem) > last_id:

                last_id = int(f.stem)
        except:
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
        Thread.__init__(self)
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
                print(e)

class ThreadLis2D(Thread):
    pass

ThreadLis()