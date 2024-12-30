"""
    图像分割
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from tqdm import tqdm
from PIL import Image


def parse_voc_xml(xml_file):
    """
    解析 VOC XML 文件，返回对象列表，每个对象包含类别和边界框坐标。
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()
    objects = []
    for obj in root.findall('object'):
        obj_struct = {}
        obj_struct['name'] = obj.find('name').text
        bbox = obj.find('bndbox')
        obj_struct['bbox'] = {
            'xmin': int(float(bbox.find('xmin').text)),
            'ymin': int(float(bbox.find('ymin').text)),
            'xmax': int(float(bbox.find('xmax').text)),
            'ymax': int(float(bbox.find('ymax').text))
        }
        objects.append(obj_struct)
    return objects


def crop_and_save(image_path, objects, output_dir, image_name_prefix):
    """
    根据对象的边界框裁剪图像，并保存到输出目录。
    """
    image = Image.open(image_path)
    width, height = image.size
    for idx, obj in enumerate(objects):
        bbox = obj['bbox']
        c_box=[bbox['xmin'], bbox['ymin'], bbox['xmax'], bbox['ymax']]
        c_box = [max(0,c_box[0]-20),max(1,c_box[1]-20),min(width,c_box[2]+20),min(height,c_box[3]+20)]
        cropped = image.crop(c_box)
        class_name = obj['name']
        # 构建保存路径，可以根据需要调整
        save_dir = os.path.join(output_dir, class_name)
        os.makedirs(save_dir, exist_ok=True)
        # 保存文件名可以包含原图名和对象索引
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        save_path = os.path.join(save_dir, f"{base_name}_{idx + 1}.jpg")
        cropped.save(save_path)
        print(f"Saved cropped image: {save_path}")


def process_dataset(images_dir, annotations_dir, output_dir):
    """
    处理整个数据集，遍历所有 XML 文件并进行裁剪。
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    xml_files = [f for f in os.listdir(annotations_dir) if f.endswith('.xml')]
    print(f"Found {len(xml_files)} XML files.")

    for xml_file in tqdm(xml_files):
        xml_path = os.path.join(annotations_dir, xml_file)
        objects = parse_voc_xml(xml_path)
        if not objects:
            print(f"No objects found in {xml_file}. Skipping.")
            continue
        # 假设图像与 XML 文件同名，仅扩展名不同
        image_filename = os.path.splitext(xml_file)[0] + '.png'  # 根据实际情况调整扩展名
        image_path = os.path.join(images_dir, image_filename)
        if not os.path.exists(image_path):
            print(f"Image file {image_filename} not found. Skipping.")
            continue
        crop_and_save(image_path, objects, output_dir, os.path.splitext(xml_file)[0])


if __name__ == "__main__":
    # 设置路径，根据实际情况修改
    images_directory = Path(fr"F:\Data\detection_by_image_list")  # 原始图像文件夹
    annotations_directory = images_directory  # XML 标注文件夹
    output_directory = images_directory.parent/"cropped_images"  # 输出小图文件夹
    output_directory.mkdir(exist_ok=True, parents=True)
    process_dataset(images_directory, annotations_directory, output_directory)
    print("Processing completed.")
