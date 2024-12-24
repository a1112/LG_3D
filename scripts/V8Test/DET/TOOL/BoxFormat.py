batch_size = 4
headTitle = ["EPOCT", "Count", "True", "False", "acc1", "重叠字符", "False2", "acc2", "False3", "acc3",
             "{}avgTime(ms)".format(batch_size)]

import copy

from shapely.geometry import Polygon
import xml.etree.ElementTree as ET
from os.path import *
from PIL import Image
from pathlib import WindowsPath
from io import BytesIO


def formatInfo(infos, rec: list):
    if not rec:
        return infos
    w, h = rec[2] - rec[0], rec[3] - rec[1]
    newInfos = []
    for info in infos:
        indexArea = getRecPolygon(info)
        intersection = indexArea.intersection(getRecPolygon(rec))
        if intersection.area / indexArea.area < 0.75:
            print("字符出界")
            continue
        newInfos.append([info[0], max(info[1] - rec[1], 0), info[2], min(info[3] - rec[1], h), *info[4:]])
    return newInfos


def getRecPolygon(obj):
    if isinstance(obj, ET.Element):
        box = [int(i.text) for i in obj[4]]
        x1, y1, x2, y2 = box
        return Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
    x1, y1, x2, y2, *_ = obj
    return Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])


def formatObjcts(objects: list, delObj=True,thershold=0.15):
    """
    正则化1 ，判断重合字符
    :param objects:
    :param delObj:
    :return:
    """
    index = 0
    hasDel = False
    if len(objects):
        argW = sum([o[2] - o[0] for o in objects]) / len(objects)
        argX = sum([objects[i + 1][0] - objects[i][0] for i in range(len(objects) - 1)]) / len(objects)
    else:
        return hasDel
    while True:
        try:
            if index == 0 or index == len(objects) - 1:
                if objects[index][5] < thershold:
                    print(objects[index][5])
                    del objects[index]
                    hasDel = True
                    continue
                if objects[index][2] - objects[index][0] < argW / 2.4:
                    del objects[index]
                    hasDel = True
                    continue
            if objects[index + 1][0] - objects[index][0] > 1.8 * argX:
                if index < len(objects) / 2:
                    del objects[index]
                else:
                    del objects[index + 1]
                hasDel = True
                continue
            indexArea = getRecPolygon(objects[index])
            intersection = indexArea.intersection(getRecPolygon(objects[index + 1]))
        except IndexError:
            break

        if intersection.area / indexArea.area > 0.7:
            if delObj:
                if objects[index][5] > objects[index + 1][5]:
                    del objects[index + 1]
                else:
                    del objects[index]
                hasDel = True
                continue
        index += 1
    return hasDel


def formatObjcts2(objects: list, delObj=True):
    """
    正则化，去除Y的巨大差异化
    1，X轴排序，选取前5Y轴第二高的数据。
    2，左右查找，Y轴相差1*平均高度，X不限制
    3，返回正则值
    :param objects:
    :param delObj:
    :return:
    """
    hasDel=False
    if len(objects) <= 10:
        return hasDel
    objects.sort(key=lambda item: item[0])
    top8 = objects[0:8].copy()
    top8.sort(key=lambda item: item[1])
    i = objects.index(top8[1])
    avgH = sum([int(obj[3] - obj[1]) for obj in objects]) / len(objects)

    def get_spaceY(objA, objB):
        return abs(objA[1] - objB[1])

    delList = []

    def traversing(direction="L"):
        nonlocal delList
        index = i
        if direction == "L":
            index2 = i - 1
        else:
            index2 = i + 1
        while True:
            if index2 < 0 or index2 >= len(objects):
                return
            if get_spaceY(objects[index], objects[index2]) > 1 * avgH:
                delList.append(index2)
            else:
                index = index2
            if direction == "L":
                index2 -= 1
            else:
                index2 += 1

    # 左右遍历
    traversing("L")
    traversing("R")
    delList.sort(reverse=True)
    for i in delList:
        del objects[i]
        hasDel=True
    return hasDel


def formatImage(image: Image.Image):
    w, h = image.size
    if -5 < w - h < 5:
        return image, [0, 0, w, h]
    newImage = Image.new("RGB", (w, w))
    image = image.convert("RGB")
    toY = int((w - h) / 2)
    rec = [0, toY, w, toY + h]
    newImage.paste(image, rec)
    return newImage, rec


def getSteelNoByXml(xml_):
    if not exists(xml_):
        return "", []
    tree = ET.parse(xml_)
    root = tree.getroot()
    objects = root.findall("object")
    objects.sort(key=lambda item: int(item[4][0].text))
    res = []
    # res = formatObjcts(objects)
    return "".join([obj[0].text for obj in objects]), res


def getImage(f_):
    img = Image.open(f_).convert("RGB")
    return formatImage(img)


def getImageByBytes(imageBytes):
    if isinstance(imageBytes, Image.Image):
        return imageBytes
    elif isinstance(imageBytes, (WindowsPath, str)):
        return Image.open(imageBytes)
    return Image.open(BytesIO(imageBytes))


def getBytesByImage(url):
    bytesIO = BytesIO()
    img = Image.open(url)
    img.save(bytesIO, format='jpeg')
    return bytesIO.getvalue()


def rotateRec(box, size):
    w, h = size
    box = list(box)
    oldBox = copy.deepcopy(box)
    box[0] = w - int(oldBox[2])
    box[1] = h - int(oldBox[3])
    box[2] = w - int(oldBox[0])
    box[3] = h - int(oldBox[1])
    return box


def getOutBox(box, size):
    """
    返回外界 正方形
    :param box:
    :param size:    :return:
    """
    minX, minY, maxX, maxY = box
    width = maxX - minX
    height = maxY - minY
    to_maxY = int(width / 2 + (maxY + minY) / 2)
    to_minY = to_maxY - width
    w, h = size
    if to_maxY > h:
        to_maxY = h
        to_minY = max(0, h - width)
    elif to_minY < 0:
        to_minY = 0
        to_maxY = min(h, to_minY + width)
    return minX, to_minY, maxX, to_maxY


def forMartBox(box, size=None, yoloBox=True):
    """
    格式化返回 yolo box
    :param box:
    :param size:
    :return:
    """
    if yoloBox:
        t_box = [int(box) for box in box]
        t_box = [t_box[1], t_box[0], t_box[3], t_box[2]]
    else:
        t_box = box
    if not size:
        return t_box
    return [max(t_box[0], 0), max(t_box[1], 0), min(t_box[2], size[0]), min(t_box[3], size[1])]
