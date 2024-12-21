from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
import concurrent.futures
import Globs
from CoilDataBase.Coil import addDefects
from Globs import serverConfigProperty
from property.Base import DataIntegrationList, DataIntegration
from utils.DetectionSpeedRecord import DetectionSpeedRecord
from .CoilMaskModel import CoilDetectionModel
from .tool import create_xml
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


def commit_defects(defect_dict, data_integration):
    defect_list = []
    for name, defect_list_ in defect_dict.items():
        defect_list_ = merge_rectangles(defect_list_)
        for defect in defect_list_:
            x1, y1, x2, y2, label_index, source = defect
            defect_list.append({
                "secondaryCoilId": data_integration.coilId,
                "surface": data_integration.key,
                "defectClass": label_index,
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
        defect_list
    )

def save_detection_item(info,image,save_url):

    if isinstance(image,np.ndarray):
        image=Image.fromarray(image)
    save_url = save_url.with_suffix(".png")
    image.save(save_url)
    w,h=image.size
    create_xml(save_url,[h,w,1],info)


def save_detection(res_list,clip_image_list,clip_info_list,id_str):
    if not id_str:
        id_str = "null"
    save_base_folder = Path(list(serverConfigProperty.surfaceConfigPropertyDict.values())[0].saveFolder).parent/"det_save"

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        index=0
        for res, clip_image, clip_info in zip(res_list, clip_image_list, clip_info_list):
            index+=1
            if not len(res):
                continue
            save_base = save_base_folder/res[0][6]/str(int(res[0][5]*10//3))
            save_base.mkdir(parents=True, exist_ok=True)
            save_url=save_base/""/f"{id_str}_{index}.png"
            executor.submit(save_detection_item,res,clip_image,save_url)

def detection_by_image(join_image,mask_image,clip_num=10,mask_threshold=0.2,id_str=None):
    if isinstance(join_image,Image.Image):
        join_image = np.array(join_image)
    if isinstance(mask_image,Image.Image):
        mask_image = np.array(mask_image)
    w = join_image.shape[1]
    h = join_image.shape[0]
    w_item_size = w // clip_num
    h_item_size = h // clip_num
    clip_image_list = []
    clip_mask_list = []
    clip_info_list = []
    for i in range(clip_num):
        for j in range(clip_num):
            c_x, c_y, c_w, c_h = w_item_size * j - 20, h_item_size * i - 20, w_item_size + 20, h_item_size + 20
            c_x, c_y, c_w, c_h = max(c_x, 0), max(c_y, 0), c_w, c_h
            if c_h < 200 or c_w < 200:
                continue
            clip_image = join_image[c_y:c_y + c_h, c_x:c_x + c_w]
            clip_mask = mask_image[c_y:c_y + c_h, c_x:c_x + c_w]

            if np.count_nonzero(clip_mask) / (clip_mask.shape[0] * clip_mask.shape[1]) > mask_threshold:
                clip_image = Image.fromarray(clip_image)
                clip_image_list.append(clip_image)
                clip_mask_list.append(clip_mask)
                clip_info_list.append((c_x, c_y, c_w, c_h))

    # print(ccm.predictImage(clip_image_list))
    res_list = cdm.predict(clip_image_list)
    if Globs.control.save_detection:
        save_detection(res_list,clip_image_list,clip_info_list,id_str)

    return res_list, clip_image_list, clip_info_list  # 目标检测

@DetectionSpeedRecord.timing_decorator("检测数据计时 检出分类")
def detection(data_integration: DataIntegration):
    join_image = data_integration.npy_image
    mask = data_integration.npy_mask
    clip_num = serverConfigProperty.clip_num
    id_str = data_integration.id_str
    res_list,clip_image_list, clip_info_list = detection_by_image(join_image,mask,clip_num,id_str)

    defect_dict = defaultdict(list)
    for res, clip_image, clip_info in zip(res_list, clip_image_list, clip_info_list):
        for box in res:
            xmin, ymin, xmax, ymax, label_index,source,name = box
            x, y, w, h = clip_info
            defect_dict[name].append((x + xmin, y + ymin, x + xmax, y + ymax,label_index, source))
    commit_defects(defect_dict, data_integration)


@DetectionSpeedRecord.timing_decorator("深度学习检测全部时间")
def detection_all(data_integration_list: DataIntegrationList):
    for dataIntegration in data_integration_list:
        detection(dataIntegration)

def detection_by_coil_id(coil_id:int):
    """
    根据 coil_id 进行 识别
    """
    for key,surface in serverConfigProperty.surfaceConfigPropertyDict.items():
        gray_image_url = surface.get_file(coil_id,surface.ImageType)
        mask_image_url = surface.get_file(coil_id,surface.MaskType)
        if not Path(gray_image_url).exists():
            continue
        gray=Image.open(gray_image_url)
        mask=Image.open(mask_image_url)
        id_str=f"{coil_id}_{key}"
        detection_by_image(gray,mask,clip_num=10,mask_threshold=0.2,id_str=id_str)
