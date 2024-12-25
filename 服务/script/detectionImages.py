import concurrent.futures

from PIL import Image
from pathlib import Path
from tqdm import tqdm

from alg.CoilMaskModel import CoilDetectionModel

batch_size = 32

cdm = CoilDetectionModel()
image_folder= Path("E:\detection_sub_image")
from alg import detection

def predict_one_batch(image_url_list):
    images=[Image.open(url) for url in image_url_list]


url_list = []
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    for image_url in image_folder.glob("*.png"):
        url_list.append(image_url)
        if len(image_url)>=batch_size:
            executor.submit(predict_one_batch,url_list.copy())
            url_list=[]
