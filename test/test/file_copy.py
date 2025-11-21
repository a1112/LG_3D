from pathlib import Path
import shutil

to_folder = Path("E:\AreaCopy")

folder_list = ["G:\Cap_S_U","G:\Cap_S_M","G:\Cap_S_D","F:\Cap_L_D","F:\Cap_L_M","F:\Cap_L_U"]
for folder in folder_list:
    for f in Path(folder).iterdir():
        if (f.name)“
        if f.is_dir():
            shutil.rmtree(f)


testFolder = Path(fr"G:\Cap_S_U\62299\area")
image_url_list = list(testFolder.glob("*.jpg"))
image_url_list.sort(key=lambda i : int(Path(i).stem))
image_url_list = image_url_list[:][::-1]
image_list = [Image.open(u) for u in image_url_list]
