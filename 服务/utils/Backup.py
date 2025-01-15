from pathlib import Path
import shutil
from CONFIG import serverConfigProperty
from threading import Thread
from .Zip import ZipAndDeletionCameraData
async def backup_image_task(from_id:int, to_id:int, save_folder:str, msg_func=None):
    from_id=int(from_id)
    to_id=int(to_id)
    save_folder=Path(save_folder)
    save_folder.mkdir(exist_ok=True, parents=True)

    thList=[]
    for key,suf in serverConfigProperty.surfaceConfigPropertyDict.items():
        for folder in suf.folderList:
            def task(folder_, msg_func_):
                for i in range(from_id, to_id):
                    f_d=Path(folder_["source"])
                    from_folder=f_d/str(i)
                    to_folder= save_folder / f_d.name / str(i)
                    if from_folder.exists():
                        shutil.copytree(from_folder,to_folder)
                zad = ZipAndDeletionCameraData(Path(save_folder / Path(folder_["source"]).name))
                zad.start()
                zad.join()
                if msg_func:
                    msg_func_(1)
            th=Thread(target=task, args=(folder, msg_func))
            th.start()
            thList.append(th)
    for th in thList:
        th.join()
    if msg_func:
        await msg_func(100)