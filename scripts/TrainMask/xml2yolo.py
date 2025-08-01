import os
import socket
import xml.etree.ElementTree as ET
from pathlib import Path


def convert_bbox(size, box):
    dw = 1. / size[0]
    dh = 1. / size[1]
    x = (box[0] + box[1]) / 2.0 - 1
    y = (box[2] + box[3]) / 2.0 - 1
    w = box[1] - box[0]
    h = box[3] - box[2]
    x = x * dw
    w = w * dw
    y = y * dh
    h = h * dh
    return x, y, w, h


def get_classes(item, classes_map_, only=False):
    for key, value in classes_map_.items():
        if only:
            return key
        if item in value:
            return key
    raise ValueError(item)


def convert_annotation(xml_path, output_path, classes_map, only=False):
    in_file = open(xml_path, encoding='utf-8')
    out_file = open(output_path, 'w', encoding='utf-8')
    tree = ET.parse(in_file)
    root = tree.getroot()
    size = root.find('size')
    w = int(size.find('width').text)
    h = int(size.find('height').text)
    classes = list(classes_map.keys())
    for obj in root.iter('object'):

        cls = obj.find('name').text
        cls = get_classes(cls, classes_map, only=only)
        if cls == "折叠,":
            cls = "折叠"
        if cls == "数据污染":
            cls = "数据脏污"
        # if cls not in classes:
        #     classes.append(cls)
        #     raise ValueError(cls)
        cls_id = classes.index(cls)
        if only:
            cls_id = 0
        xmlbox = obj.find('bndbox')
        b = (float(xmlbox.find('xmin').text), float(xmlbox.find('xmax').text),
             float(xmlbox.find('ymin').text), float(xmlbox.find('ymax').text))
        bb = convert_bbox((w, h), b)
        out_file.write(str(cls_id) + " " + " ".join([str(a) for a in bb]) + '\n')
    print(classes)


def process_annotations(xml_folder, yolo_folder, classes_map, only=False):
    if not os.path.exists(yolo_folder):
        os.makedirs(yolo_folder)

    xml_files = [f for f in os.listdir(xml_folder) if f.endswith('.xml')]

    for xml_file in xml_files:
        xml_path = os.path.join(xml_folder, xml_file)
        yolo_path = os.path.join(yolo_folder, xml_file.replace('.xml', '.txt'))
        convert_annotation(xml_path, yolo_path, classes_map, only=only)
        print(f"Converted {xml_file} to YOLO format.")


# 定义类别（确保这些类别与你的XML文件中的类别一致）
classes_ = ['凹坑', '封口', '划伤', '烂边', '毛边', '数据缺失', '粘连', '折叠', '毛刺', '边部脏污', '脏污', '数据脏污',
            '数据遮挡', '边裂', '分层', '卷边', '卷尾', '塔形', '结疤', '卷头', '大卷边']

classes_map = {
    "数据": ['粘连', '毛边', '边部脏污',"背景_头尾", '脏污',"背景_小型", '烂边', '数据缺失', '数据脏污', '封口', '数据遮挡', "数据污染"],
    "细微": ['划伤', '凹坑', '毛刺',"小型缺陷", '边裂', '结疤', "起皮"],
    "严重": ['折叠',"边部褶皱","毛刺烂边", '卷边', '大卷边', "折叠,", "外折叠","刮丝"],
    "其他": ["卷头", '分层', '卷尾', '塔形', "头尾", "打包带", "检出", "背景"],
    "内折叠": ["内折叠"]
}

print(socket.gethostname())

if socket.gethostname() == "lcx_ace":
    # 示例使用
    xml_folder = Path(r'F:\subImage\样本_合并')
    yolo_folder = xml_folder.parent / "txt"
    yolo_folder.mkdir(parents=True, exist_ok=True)
    process_annotations(xml_folder, yolo_folder, classes_map, only=True)

if socket.gethostname() == "DESKTOP-94ADH1G":
    xml_folder = Path(r'G:\data\Copy\Copy')
    yolo_folder = xml_folder.parent / "txt"
    yolo_folder.mkdir(parents=True, exist_ok=True)
    process_annotations(xml_folder, yolo_folder, classes_map, only=True)