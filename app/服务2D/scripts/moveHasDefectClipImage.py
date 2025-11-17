from CoilDataBase import Coil
from pathlib import Path
import shutil
from tqdm import tqdm
file_list = Path(fr"j:/cropped_moved_2").glob("*.jpg")
save_folder = Path(fr"j:/cropped_moved_3")
print(file_list)
save_folder.mkdir(parents=True, exist_ok=True)
coil_set =set()
for item in Coil.defects():
    if item.defectName in ["折叠"]:
        coil_set.add(item.secondaryCoilId)

for file in tqdm(file_list):
    coil_id = int(file.stem.split("_")[1])
    if coil_id in coil_set:
        shutil.copy(file,save_folder/file.name)
        image_url= file.with_suffix(".jpg")
        shutil.copy(image_url,save_folder/image_url.name)