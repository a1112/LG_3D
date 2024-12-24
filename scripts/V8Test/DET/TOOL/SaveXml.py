import copy
import os
from xml.etree import ElementTree as ET

import PIL.Image


def crateObjectItem(objItem, itemData, outBox):
    #  [564, 632, 611, 683, '2'],
    item = copy.deepcopy(objItem)
    item[0].text = str(itemData[4])
    for i, value in enumerate(itemData[0:4]):
        if i in [0, 2]:
            item[4][i].text = str(int(value) + int(outBox[0]))
        else:
            item[4][i].text = str(int(value) + int(outBox[1]))
    return item


def tryCreateFileDir(f_path):
    """
    创建文件夹
    :param f_path:
    :return:
    """
    if os.path.isfile(f_path):
        f_path = os.path.dirname(f_path)
    if not os.path.exists(f_path):
        os.makedirs(f_path)


def saveXml(info, image, fileUrl, outBox=None):
    size=image
    if isinstance(image, PIL.Image.Image):
        size=image.size
    fileUrl = str(fileUrl)
    if outBox is None:
        outBox = [0, 0]
    tempFile = os.path.join(os.getcwd(), "template/yolo.xml")
    tree = ET.parse(tempFile)
    root = tree.getroot()
    objItem = copy.deepcopy(root[-1])
    root.remove(root[-1])
    root[0].text, root[1].text = os.path.split(fileUrl)
    root[2].text = fileUrl
    root[4][0].text, root[4][1].text = [str(i) for i in size]
    for itemInfo in info:
        root.append(crateObjectItem(objItem, itemInfo, outBox))
    outF = fileUrl.replace(".jpg", ".xml")
    if os.path.exists(outF):
        os.remove(outF)
    tree.write(outF)
