import os
import xml.etree.ElementTree as ET
from pathlib import Path
from tqdm import tqdm

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


def convert_annotation(xml_path, output_path, classes,getClasses=False):
    in_file = open(xml_path, encoding='utf-8')
    out_file = open(output_path, 'w', encoding='utf-8')
    tree = ET.parse(in_file)
    root = tree.getroot()
    size = root.find('size')
    w = int(size.find('width').text)
    h = int(size.find('height').text)

    for obj in root.iter('object'):
        cls = obj.find('name').text
        if cls == "封口":
            cls = "打包带"
        if cls == "折叠,":
            cls = "折叠"
        if cls == "数据污染":
            cls = "数据脏污"
        if cls == "大卷边":
            cls= "卷边"


        if getClasses:
            if cls not in classes:
                classes.append(cls)
            continue
        if cls not in classes:
            raise ValueError(f"Class '{cls}' not found in classes list.")
        cls_id = classes.index(cls)
        xmlbox = obj.find('bndbox')
        b = (float(xmlbox.find('xmin').text), float(xmlbox.find('xmax').text),
             float(xmlbox.find('ymin').text), float(xmlbox.find('ymax').text))
        bb = convert_bbox((w, h), b)
        out_file.write(str(cls_id) + " " + " ".join([str(a) for a in bb]) + '\n')
    print(classes)



def process_annotations(xml_folder, yolo_folder, classes):
    if not os.path.exists(yolo_folder):
        os.makedirs(yolo_folder)

    xml_files = [f for f in os.listdir(xml_folder) if f.endswith('.xml')]

    for xml_file in tqdm(xml_files):
        xml_path = os.path.join(xml_folder, xml_file)
        yolo_path = os.path.join(yolo_folder, xml_file.replace('.xml', '.txt'))
        convert_annotation(xml_path, yolo_path, classes)
        print(f"Converted {xml_file} to YOLO format.")


# 定义类别（确保这些类别与你的XML文件中的类别一致）
classes = ['折叠', '划伤', '凹坑', '粘连', '毛刺', '数据缺失', '脏污', '烂边', '边部脏污', '数据脏污', '边裂', '数据遮挡', '打包带', '毛边', '分层', '卷尾', '塔形', '卷边', '结疤', '卷头', '大卷边']
#


# 示例使用
xml_folder = Path(r'D:\样本\中间增加_合并')
yolo_folder = xml_folder.parent / "txt"
yolo_folder.mkdir(parents=True, exist_ok=True)
process_annotations(xml_folder, yolo_folder, classes)
