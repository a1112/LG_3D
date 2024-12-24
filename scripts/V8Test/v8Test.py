"""
用来定位数据位置
"""
from pathlib import Path
from pathlib import Path
from ultralytics import YOLO
from PIL import Image

import config
from .DET.TOOL.SaveXml import saveXml

model = YOLO(r"detection_yolov8_test1/best.pt")

saveErrorFolderBase = Path(r"E:/ERROR") / "yoloError"


def filterInfo(info: list, image, imageName):
    saveErrorFolder = None
    for i in info:
        i[4] = ['起泡', '接缝', '脏污', '脱皮', '标签', '裂纹', '坑', '划伤', '边烂', '印记'][i[4]]
        if i[4] not in ["起泡", "裂纹","边烂"]:
            return []
    if not info:
        return info
    if len(info) > 1:
        #  触发数量异常
        saveErrorFolder = saveErrorFolderBase / "countError"

    elif any([i[5] < 0.8 for i in info]):
        saveErrorFolder = saveErrorFolderBase / "sourceError"
    if saveErrorFolder:
        saveErrorFolder.mkdir(exist_ok=True, parents=True)
        image.save(saveErrorFolder / Path(imageName).name)
        saveXml(info, image, saveErrorFolder / Path(imageName).with_suffix(".xml").name)
    # end Save
    info.sort(key=lambda i: i[5], reverse=True)
    return info[0]


def predict(image, imageName):
    info = config.get_boxes(model(image))
    box = filterInfo(info, image, imageName)
    if not box:
        return None
    h, w = image.size
    x, y, x1, y1 = box[:4]
    if y1 - y < h / 3.5 and (y < 10 or y1 > h - 10):
        return False
    x, y, x1, y1 = x - 50, y - 20, x1 + 50, y1 + 20
    cropImage = image.crop((x, y, x1, y1))
    cropImage = cropImage.transpose(Image.Transpose.ROTATE_270)
    return cropImage.rotate(-1)


if __name__ == "__main__":
    root = Path(r"E:\ERROR\sourceError\sourceError")
    for file_ in root.glob("*.jpg"):
        try:
            image = Image.open(file_)
            predict(image, file_)
        except:
            pass
