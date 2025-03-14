from pathlib import Path
import numpy as np
from PIL import Image

from PIL import Image
saveFolder = Path(fr"I:\database\2D")
saveFolder.mkdir(exist_ok=True)
for folder in [Path(mosaic.saveFolder),Path(mosaic.saveFolder)]:
    # 裁剪出表面数据，进行分类处理
    for itemFolder in folder.iterdir():
        print(itemFolder)
        try:
            grayImage = Image.open(itemFolder / "GRAY.png")
            maskImage = Image.open(itemFolder / "MASK.png")
            grayImage = np.asarray(grayImage)
            maskImage = np.asarray(maskImage)
            n = 10
            h_item_size = maskImage.shape[0]//n
            w_item_size = maskImage.shape[1]//n
            coilName = itemFolder.name
            for i in range(n):
                for j in range(n):
                    x,y,w,h = w_item_size*j,h_item_size*i,w_item_size,h_item_size
                    clip_image = grayImage[h_item_size*i:h_item_size*(i+1), w_item_size*j:w_item_size*(j+1)]
                    clip_mask = maskImage[h_item_size * i:h_item_size * (i + 1), w_item_size * j:w_item_size * (j + 1)]
                    if np.count_nonzero(clip_mask)/(clip_mask.shape[0]*clip_mask.shape[1]) > 0.3:
                        saveName = saveFolder / f"{coilName}_{mosaic.key}_{i}_{j}_{x}_{y}_{w}_{h}.png"
                        Image.fromarray(clip_image).save(saveName)
        except FileNotFoundError:
            pass