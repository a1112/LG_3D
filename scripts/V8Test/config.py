from pathlib import Path

camera1Folder = Path(r"D:\cam_1")  # 来源

hasCharFolder = Path( r"D:\保存")
notHasCharFolder = r"D:\cam_1_un_char"
Path(hasCharFolder).mkdir(exist_ok=True,parents=True)
saveFolder = Path(r"E:/SAVE")  # 保存的路径
errorFolder = Path(r"E:/ERROR")  # 保存的路径
commitFolder = Path(r"E:/COMMIT/RUN")
testOutFolder = Path(r"E:/COMMIT/TEST_out")

testFolder = Path(r"E:/COMMIT/TEST")  # 来源

commitFolder.mkdir(exist_ok=True, parents=True)
testOutFolder.mkdir(exist_ok=True, parents=True)


def get_boxes(boxes):
    boxes = boxes.pop().boxes

    xywh_es = boxes.xyxy
    cls_es = boxes.cls
    conf_es = boxes.conf
    boxList = []
    for xywh, cls, conf in zip(xywh_es, cls_es, conf_es):
        boxList.append(list(xywh.cpu().numpy().tolist()) + [int(cls)] + [float(conf.cpu().numpy().tolist())])
    boxList.sort(key=lambda item: item[0])
    return boxList


def tryGetInt(name):
    try:
        return int(name)
    except BaseException as e:
        return 1


def getMaxSig():
    return max([tryGetInt(f) for f in saveFolder.glob("*") if f.is_dir()]+[1])

def mkMaxSigFolder(sig):
    return (saveFolder/f"{sig}").mkdir(exist_ok=True, parents=True)
