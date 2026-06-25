import logging
import shutil
import socket
from pathlib import Path

from PIL import ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True
logger = logging.getLogger(__name__)


def do_files(files, class_name, names, to_folder, file_func):
    to_folder = Path(to_folder)
    for file_, name in zip(files, names):
        if class_name == name:
            out_file = to_folder / "相同" / name / file_.name
        else:
            out_file = to_folder / "不同" / name / file_.name
        out_file.parent.mkdir(exist_ok=True, parents=True)
        file_func(file_, out_file)


def classifiers_folder(from_folder, out_folder, file_func):
    from Base.alg import detection

    ccm = detection.ccm
    for file_folder in from_folder.glob("*"):
        file_folder = Path(file_folder)
        logger.debug("classify folder: %s", file_folder)
        if not file_folder.is_dir():
            logger.debug("skip non-folder: %s", file_folder)
            continue
        class_name = file_folder.name
        files = list(file_folder.glob("*.*"))
        file_len = len(files)
        count_len = 640
        for i in range(file_len // count_len + 1):
            logger.debug("classify batch %s in %s", i, file_folder)
            files_c = files[i * count_len:(i + 1) * count_len]
            _, _, names = ccm.predict_image(files_c)
            do_files(files_c, class_name, names, out_folder, file_func)


def default_folders():
    from_folder = Path("I:/detection_save6/classifier")
    out_folder = from_folder.parent / "classifier_out"
    if socket.gethostname() == "DESKTOP-V9D92AP":
        from_folder = Path("G:/数据优化/SaveDefect/SaveDefect")
        out_folder = from_folder.parent / "classifier_out"
    return from_folder, out_folder


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    source_folder, target_folder = default_folders()
    classifiers_folder(from_folder=source_folder, out_folder=target_folder, file_func=shutil.move)
