from pathlib import Path
import shutil
from Globs import serverConfigProperty
from threading import Thread
from .Zip import ZipAndDeletionCameraData
async def backupImageTask(fromId:str, toId:str, saveFolder:str,msgFunc=None):
    fromId=int(fromId)
    toId=int(toId)
    saveFolder=Path(saveFolder)
    saveFolder.mkdir(exist_ok=True,parents=True)

    thList=[]
    for key,suf in serverConfigProperty.surfaceConfigPropertyDict.items():
        for folder in suf.folderList:
            def task(folder_, msg_func_):
                for i in range(fromId,toId):
                    f_d=Path(folder_["source"])
                    from_folder=f_d/str(i)
                    to_folder=saveFolder/f_d.name/str(i)
                    if from_folder.exists():
                        shutil.copytree(from_folder,to_folder)
                zad = ZipAndDeletionCameraData(Path(saveFolder / Path(folder_["source"]).name))
                zad.start()
                zad.join()
                if msgFunc:
                    msg_func_(1)
            th=Thread(target=task,args=(folder,msgFunc))
            th.start()
            thList.append(th)
    for th in thList:
        th.join()
    if msgFunc:
        await msgFunc(100)