from pathlib import Path

import cv2
import numpy as np
import os
from lxml import etree


def find_bounding_boxes(mask):
    mask[mask>0]= 255
    unique_labels = np.unique(mask)
    bounding_boxes = []

    for label in unique_labels:
        if label == 0:  # 忽略背景
            continue
        # 找到每个标签的轮廓
        binary_mask = np.uint8(mask == label)
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            if cv2.contourArea(contour) < 100:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            bounding_boxes.append((label, x, y, x + w, y + h))

    return bounding_boxes


def create_xml(file_name, img_shape, bounding_boxes):
    annotation = etree.Element("annotation")

    folder = etree.SubElement(annotation, "folder")
    folder.text = "images"

    filename = etree.SubElement(annotation, "filename")
    filename.text = file_name

    size = etree.SubElement(annotation, "size")
    width = etree.SubElement(size, "width")
    width.text = str(img_shape[1])
    height = etree.SubElement(size, "height")
    height.text = str(img_shape[0])
    depth = etree.SubElement(size, "depth")
    depth.text = str(img_shape[2])

    for bbox in bounding_boxes:
        label, xmin, ymin, xmax, ymax = bbox
        object = etree.SubElement(annotation, "object")

        name = etree.SubElement(object, "name")
        name.text = str(label)

        bndbox = etree.SubElement(object, "bndbox")
        xmin_elem = etree.SubElement(bndbox, "xmin")
        xmin_elem.text = str(xmin)
        ymin_elem = etree.SubElement(bndbox, "ymin")
        ymin_elem.text = str(ymin)
        xmax_elem = etree.SubElement(bndbox, "xmax")
        xmax_elem.text = str(xmax)
        ymax_elem = etree.SubElement(bndbox, "ymax")
        ymax_elem.text = str(ymax)

    tree = etree.ElementTree(annotation)
    return tree


def process_masks(mask_folder, xml_folder):
    mask_files = [f for f in os.listdir(mask_folder) if os.path.isfile(os.path.join(mask_folder, f))]

    for mask_file in mask_files:
        mask_path = os.path.join(mask_folder, mask_file)
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        bounding_boxes = find_bounding_boxes(mask)

        img_shape = (mask.shape[0], mask.shape[1], 3)  # 假设图像是RGB的
        file_name = os.path.basename(mask_file)  # 假设mask和图像文件名相同

        xml_tree = create_xml(file_name, img_shape, bounding_boxes)
        xml_output_path = os.path.join(xml_folder, mask_file.replace('MASK.png', 'GRAY.xml')
                                       .replace('MASK.jpg', 'GRAY.xml'))
        xml_tree.write(xml_output_path, pretty_print=True, xml_declaration=True, encoding="utf-8")
        print(f"Saved XML for {mask_file} to {xml_output_path}")


# 示例使用
mask_folder = Path(fr'F:\ALG\SegTrainTest\trainTest\dataList\SaveMask\mask')
xml_folder = mask_folder.parent/'xml'
xml_folder.mkdir(parents=True, exist_ok=True)
process_masks(mask_folder, xml_folder)
