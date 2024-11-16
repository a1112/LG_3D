from pathlib import Path
import shutil
from CONFIG import serverConfigProperty
from threading import Thread
from .Zip import ZipAndDeletion
async def backupImageTask(fromId:str, toId:str, saveFolder:str,msgFunc=None):
    fromId=int(fromId)
    toId=int(toId)
    saveFolder=Path(saveFolder)
    saveFolder.mkdir(exist_ok=True,parents=True)

    thList=[]
    for key,suf in serverConfigProperty.surfaceConfigPropertyDict.items():
        for folder in suf.folderList:
            def task(folder_,msgFunc_):
                for i in range(fromId,toId):
                    f_d=Path(folder_["source"])
                    fromFolder=f_d/str(i)
                    toFolder=saveFolder/f_d.name/str(i)
                    if fromFolder.exists():
                        shutil.copytree(fromFolder,toFolder)
                zad = ZipAndDeletion(Path(saveFolder/Path(folder_["source"]).name))
                zad.start()
                zad.join()
                if msgFunc:
                    msgFunc_(1)
            th=Thread(target=task,args=(folder,msgFunc))
            th.start()
            thList.append(th)
    for th in thList:
        th.join()
    if msgFunc:
        await msgFunc(100)