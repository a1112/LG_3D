from tqdm import tqdm
from pathlib import Path
from Base.alg.CoilClsModel import CoilClsModel
import shutil
model = CoilClsModel()
print(model)

image_folder = Path(fr"E:\train\检出")
image_save = image_folder.parent/"cls_out"
image_save.mkdir(exist_ok=True, parents=True)
step=32
index=0
image_lists = list(image_folder.glob("*.jpg"))
for i in tqdm(range(0,len(image_lists),32)) :
    sub_str=image_lists[i:i + 32]
    res_index, res_source,names = model.predict_image(sub_str)
    for url,cls_index, source,name in zip(sub_str,res_index,res_source,names):
        save_folder=image_save/name
        save_folder.mkdir(exist_ok=True, parents=True)
        shutil.copy(url,save_folder/url.name)

# res_index,res_source = model.predict_image()
# print(res_source)