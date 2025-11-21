from concurrent.futures import ThreadPoolExecutor

from tqdm import tqdm
from pathlib import Path,WindowsPath

from PIL import Image
Image.MAX_IMAGE_PIXELS = None

from_folder = Path(fr"J:\area_copy_to_folder")
save_folder = Path(fr"J:\area_copy_to_folder_cropped")
save_folder.mkdir(parents=True, exist_ok=True)
def task_image(image_url:WindowsPath):
    image = Image.open(image_url)
    h,w = image.size
    h_num = h//1024
    w_num = w//1024
    for y in range(h_num):
        for x in range(w_num):
            save_path = save_folder.joinpath(f"{image_url.parent.parent.name}_{image_url.parent.name}_{y}_{x}.jpg")
            image.crop((x*1024,y*1024,(x+1)*1024,(y+1)*1024)).save(save_path)

for file_ in tqdm(from_folder.glob("*/*/*.jpg")):

    with ThreadPoolExecutor(max_workers = 16) as executor:

        executor.submit(task_image,file_)

