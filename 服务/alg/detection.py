import time
from collections import defaultdict
import numpy as np
from PIL import Image

from Globs import serverConfigProperty
from property.Base import DataIntegrationList
from utils.DetectionSpeedRecord import DetectionSpeedRecord
from .CoilMaskModel import CoilDetectionModel

from CoilDataBase.Coil import addDefects

cdm = CoilDetectionModel()


def rectangles_overlap(rect1, rect2):
    """
    判断两个矩形是否重叠。
    """
    x1, y1, x2, y2,*_ = rect1
    a1, b1, a2, b2,*_ = rect2

    return not (x2 < a1 or a2 < x1 or y2 < b1 or b2 < y1)


def merge_two_rectangles(rect1, rect2):
    """
    合并两个重叠的矩形，返回合并后的矩形。
    """
    x1 = min(rect1[0], rect2[0])
    y1 = min(rect1[1], rect2[1])
    x2 = max(rect1[2], rect2[2])
    y2 = max(rect1[3], rect2[3])
    *_,index,source1 = rect1
    *_,source2 = rect2
    return [x1, y1, x2, y2,index,max(source1,source2)]


def merge_rectangles(rectangles):
    """
    合并重叠的矩形。
    """
    print("merge_rectangles  :",rectangles)
    if not rectangles:
        return []

    merged_rects = []
    while rectangles:
        # 取出第一个矩形
        rect = rectangles.pop(0)
        merged = False

        # 遍历合并结果列表，检查是否有重叠的矩形
        for i, mrect in enumerate(merged_rects):
            if rectangles_overlap(rect, mrect):
                # 如果重叠，合并并更新列表
                merged_rects[i] = merge_two_rectangles(rect, mrect)
                merged = True
                break

        if not merged:
            # 如果没有合并，则直接添加到结果列表
            merged_rects.append(rect)

        # 检查并继续合并可能由于新矩形合并后的其他重叠
        for i in range(len(merged_rects) - 1, -1, -1):
            for j in range(i):
                if rectangles_overlap(merged_rects[i], merged_rects[j]):
                    merged_rects[j] = merge_two_rectangles(merged_rects[i], merged_rects[j])
                    merged_rects.pop(i)
                    break

    return merged_rects


def commitDefects(defectDict,dataIntegration):
    defectList = []
    for name, defectList_ in defectDict.items():
        defectList_ = merge_rectangles(defectList_)
        for defect in defectList_:
            x1, y1, x2, y2, labelIndex, source = defect
            print("source ",source)
            defectList.append({
                "secondaryCoilId": dataIntegration.coilId,
                "surface": dataIntegration.key,
                "defectClass": labelIndex,
                "defectName": name,
                "defectStatus": 0,
                "defectX": x1,
                "defectY": y1,
                "defectW": x2 - x1,
                "defectH": y2 - y1,
                "defectSource": source,
                "defectData":""
            })
    # deleteDefectsBySecondaryCoilId(coilState.coilId,coilState.key)
    addDefects(
        defectList
    )

@DetectionSpeedRecord.timing_decorator("检测数据计时 检出分类")
def detection(dataIntegration):
    npyData = dataIntegration.npyData
    joinImage = dataIntegration.joinImage
    mask = dataIntegration.npy_mask
    clip_num = serverConfigProperty.clip_num
    # use AlgorithmFactory to create a detection model
    w_item_size = mask.shape[1] // clip_num
    h_item_size = mask.shape[0] // clip_num
    clip_image_list = []
    clip_mask_list = []
    clio_info_list = []
    for i in range(clip_num):
        for j in range(clip_num):
            x, y, w, h = w_item_size * j, h_item_size * i, w_item_size, h_item_size
            clip_image = joinImage[h_item_size * i:h_item_size * (i + 1), w_item_size * j:w_item_size * (j + 1)]
            clip_mask = mask[h_item_size * i:h_item_size * (i + 1), w_item_size * j:w_item_size * (j + 1)]
            if h < 300 or w < 300:
                continue
            if np.count_nonzero(clip_mask) / (clip_mask.shape[0] * clip_mask.shape[1]) > 0.3:
                clip_image = Image.fromarray(clip_image)
                clip_image_list.append(clip_image)
                # clip_image.save(fr"I:\database\yoloError\to\clip_image_{coilState.coilId}_{coilState.direction}_{i}_{j}.png")
                clip_mask_list.append(clip_mask)
                clio_info_list.append((x, y, w, h))

    # print(ccm.predictImage(clip_image_list))
    resList = cdm.predict(clip_image_list)  #  目标检测
    defectDict = defaultdict(list)

    for res, clip_image, clip_info in zip(resList, clip_image_list, clio_info_list):
        for box in res:
            xmin, ymin, xmax, ymax, labelIndex,source,name = box
            x, y, w, h = clip_info
            defectDict[name].append((x + xmin, y + ymin, x + xmax, y + ymax,labelIndex, source))
    commitDefects(defectDict,dataIntegration)


@DetectionSpeedRecord.timing_decorator("深度学习检测全部时间")
def detectionAll(dataIntegrationList: DataIntegrationList):
    for dataIntegration in dataIntegrationList:
        detection(dataIntegration)
