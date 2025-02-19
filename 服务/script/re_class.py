from pathlib import Path
import socket

import shutil
from pathlib import Path
import concurrent.futures
# 根据ID 检测
from sqlalchemy.util import await_only

import Globs
from alg import detection

ccm = detection.ccm


def do_files(files, class_name, names, to_folder, file_func):
    to_folder = Path(to_folder)
    # to_folder.mkdir(exist_ok=True,parents=True)
    for file_, name in zip(files, names):
        if class_name == name:
            out_file = to_folder / "相同" / name / file_.name
        else:
            out_file = to_folder / "不同" / name / file_.name
        out_file.parent.mkdir(exist_ok=True, parents=True)
        file_func(file_, out_file)


def classifiers_folder(from_folder, out_folder, file_func):
    for file_folder in from_folder.glob("*"):
        file_folder = Path(file_folder)
        print(file_folder)
        if not file_folder.is_dir():
            continue
        class_name = file_folder.name
        files = list(file_folder.glob("*.png"))
        res_index, res_source, names = ccm.predict_image(files)
        do_files(files, class_name, names, out_folder, file_func)


from_ = Path(fr"E:\detection_save6\classifier")
out_ = from_.parent / "classifier_out"
func = shutil.move
if socket.gethostname() == "lcx_ace":
    from_ = Path(fr"I:\detection_save6\classifier")
    out_ = from_.parent / "classifier_out"
classifiers_folder(from_folder=from_, out_folder=out_, file_func=func)
