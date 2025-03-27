from pathlib import Path
from PIL import Image

testFolder = Path(fr"G:\Cap_S_D\62094\area")
image_url_list = list(testFolder.glob("*.jpg"))
image_url_list.sort(key=lambda i : int(Path(i).stem))
image_url_list = image_url_list[11:]
image_list = [Image.open(u) for u in image_url_list]

# 拼接图像
