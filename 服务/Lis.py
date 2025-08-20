import os
import time
from pathlib import Path
from threading import Thread
from CoilDataBase.Coil import get_secondary_coil

import psutil

def kill_process(name):
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == name:
            try:
                proc.kill()
                print(f"成功终止 {name}")
            except psutil.AccessDenied:
                print(f"权限不足，无法终止 {name}")
            except Exception as e:
                print(f"终止进程时出错: {e}")


def get_folder_last_id():
    last_id= 0
    for f in Path(fr"G:\Cap_S_U").iterdir():
        try:
            if int(f.stem) > last_id:

                last_id = int(f.stem)
        except:
            continue
    return last_id


class ThreadLis(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.start()

    def run(self):
        scan_last = get_folder_last_id()
        while True:
            time.sleep(30)
            last_secondary = get_secondary_coil(1)[0]
            last_id = last_secondary.Id
            print(fr"扫描 CapTure 状态 last_secondary：{last_secondary} scan_last：{scan_last}")
            if last_secondary > (scan_last+3):
                kill_process("CapTure.exe")
                scan_last = last_id
            else:
                scan_last = max(get_folder_last_id(),scan_last)
