import socket
from pathlib import Path
import concurrent.futures
from tkinter import Image

from Base.alg import detection
from Base.alg.CoilMaskModel import CoilDetectionModel
from PIL import Image

cdm = CoilDetectionModel()

images_folder = Path(fr"D:\标志\标记06")
if "DESKTOP-V9D92AP" == socket.gethostname():
    save_base_folder = Path(fr"E:\detection_save")

batch_size = 16


def predict_images(files, cdm_):
    return detection.detection_by_image_list(files, cdm_)


with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    image_url_list = []
    for image_url in images_folder.glob("*.png"):
        image_url_list.append(image_url)
        if len(image_url_list) >= batch_size:
            result = executor.submit(predict_images, image_url_list, cdm_=cdm)
            image_url_list = []
