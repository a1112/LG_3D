from tqdm import tqdm
from pathlib import Path
import shutil


from_folder_list = ["D:\Save_S", "E:\Save_L"]
from_folder_list  = [list(Path(f).iterdir()) for f in from_folder_list]
to_folder = Path("D:\SaveDefect")
for from_folder in tqdm(from_folder_list[0]+from_folder_list[1]):
    from_folder = Path(from_folder)
    image_url_list = list(from_folder.glob("classifier/*/*.png"))
    for image_url in image_url_list:
        to_url = to_folder/image_url.parent.name/image_url.name
        if to_url.exists():
            continue
        to_url.parent.mkdir(exist_ok=True,parents=True)
        image = shutil.copy(image_url, to_url)
