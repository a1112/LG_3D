import numpy as np
from ultralytics import YOLO
from PIL import Image
from pathlib import Path
from lxml import etree


def create_xml(file_name, img_shape, bounding_boxes, output_folder):
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
        obj = etree.SubElement(annotation, "object")

        name = etree.SubElement(obj, "name")
        name.text = str(label)

        bndbox = etree.SubElement(obj, "bndbox")
        xmin_elem = etree.SubElement(bndbox, "xmin")
        xmin_elem.text = str(xmin)
        ymin_elem = etree.SubElement(bndbox, "ymin")
        ymin_elem.text = str(ymin)
        xmax_elem = etree.SubElement(bndbox, "xmax")
        xmax_elem.text = str(xmax)
        ymax_elem = etree.SubElement(bndbox, "ymax")
        ymax_elem.text = str(ymax)

    tree = etree.ElementTree(annotation)
    xml_path = Path(output_folder) / (Path(file_name).stem + '.xml')
    tree.write(str(xml_path), pretty_print=True, xml_declaration=True, encoding="utf-8")
    print(f"Saved XML to {xml_path}")


# 加载模型
model = YOLO(r"F:\ALG\SegTrainTest\trainTest\dataList\coilMask\runs\detect\train2\weights\best.pt")

# 图片和XML输出文件夹
image_folder = Path(r"F:\ALG\SegTrainTest\trainTest\dataList\coilMask\S_D")
xml_output_folder = Path(r"F:\ALG\SegTrainTest\trainTest\dataList\coilMask\Annotations")

if not xml_output_folder.exists():
    xml_output_folder.mkdir(parents=True)

# 处理图片并保存预测结果为XML
for image_file in image_folder.glob("*.png"):
    image = Image.open(image_file)
    results = model(image)  # 在图像上进行预测

    bounding_boxes = []
    for result in results:
        for box in result.boxes:
            xyxy = box.xyxy[0].cpu().numpy()
            label = int(box.cls[0].cpu().numpy())  # 假设类标签是整数
            xmin, ymin, xmax, ymax = xyxy
            bounding_boxes.append((label, int(xmin), int(ymin), int(xmax), int(ymax)))

    img_shape = (image.height, image.width, 3)  # 假设图像是RGB的
    create_xml(image_file.name, img_shape, bounding_boxes, xml_output_folder)
