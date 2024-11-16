import numpy as np
from ultralytics import YOLO
from PIL import Image
from pathlib import Path
# Load a model
model = YOLO("best.pt")  # load a custom model


for imageFile in Path(r"F:\ALG\SegTrainTest\trainTest\dataList\cropMask\pre\image").glob("*.png"):
    saveFolder = Path(r"F:\ALG\SegTrainTest\trainTest\dataList\cropMask\pre\mask")
    saveFolder.mkdir(parents=True, exist_ok=True)
    results = model(str(imageFile))  # predict on an image
    if results[0].masks:
        orig_shape = results[0].masks.orig_shape
        Image.fromarray((results[0].masks.data[0].cpu().numpy()*255).astype(np.uint8)).resize(orig_shape).save(saveFolder/imageFile.name)  # display segmentation mask
