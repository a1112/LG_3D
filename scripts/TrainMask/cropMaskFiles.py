
from pathlib import Path

from PIL import Image
import numpy as np
rootFolder = Path(r"F:\ALG\SegTrainTest\trainTest\dataList\coilMask")

saveFolder = rootFolder.parent / "cropMask"
maskSaveFolder = saveFolder / "mask"
imageSaveFolder = saveFolder / "image"
maskSaveFolder.mkdir(parents=True, exist_ok=True)
imageSaveFolder.mkdir(parents=True, exist_ok=True)

for imageFile in rootFolder.glob("*/*_GRAY.png"):
    image = Image.open(imageFile)
    maskFile = Image.open(imageFile.parent/(imageFile.name.replace("GRAY", "MASK")))
    w,h = image.size
    mask = np.array(maskFile)
    image = np.array(image)

    n = (h - w) // (w // 2) + 1

    # 计算每个切割区域的起始点
    step = (h - w) // (n - 1)

    for i in range(n):
        start_y = i * step
        end_y = start_y + w
        if end_y > h:
            end_y = h
            start_y = h - w

        cropped_image = image[start_y:end_y, :]
        cropped_mask = mask[start_y:end_y, :]
        cropped_image = Image.fromarray(cropped_image)
        cropped_image = cropped_image.resize((640, 640))
        cropped_mask = Image.fromarray(cropped_mask)
        cropped_mask = cropped_mask.resize((640, 640))
        cropped_image.save(imageSaveFolder / (imageFile.name.replace(".png", f"_{i}.png")))
        cropped_mask.save(maskSaveFolder / (imageFile.name.replace(".png", f"_{i}.png")))
