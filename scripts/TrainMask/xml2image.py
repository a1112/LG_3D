# 根据 xml 剪切 image 到 folder

import os
from pathlib import Path

import cv2
import xml.etree.ElementTree as ET
from PIL import Image
from tqdm import tqdm
import numpy as np

def crop_images_from_xml(xml_folder, image_folder, output_folder):
    """
    根据VOC格式的XML文件剪切图像中的目标区域

    参数:
        xml_folder: 存放XML标注文件的文件夹路径
        image_folder: 存放原始图像的文件夹路径
        output_folder: 保存剪切后小图的文件夹路径
    """
    # 确保输出文件夹存在
    os.makedirs(output_folder, exist_ok=True)

    # 遍历XML文件夹中的所有文件
    for xml_file in os.listdir(str(xml_folder)):
        if not xml_file.endswith('.xml'):
            continue

        # 解析XML文件
        xml_path = os.path.join(xml_folder, xml_file)
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # 获取对应的图像文件
        image_filename = root.find('filename').text
        image_path = os.path.join(image_folder, image_filename)

        # # 检查图像文件是否存在
        # if not os.path.exists(image_path):
        #     print(f"警告: 图像文件 {image_path} 不存在，跳过")
        #     continue

        # 读取图像
        if not Path(image_path).exists():
            continue
        image = Image.open(image_path)
        image = np.array(image)
        if image is None:
            print(f"警告: 无法读取图像 {image_path}，跳过")
            continue

        # 遍历所有目标对象
        for i, obj in enumerate(root.findall('object')):
            # 获取类别名
            class_name = obj.find('name').text

            # 获取边界框坐标
            bbox = obj.find('bndbox')
            xmin = int(float(bbox.find('xmin').text))
            ymin = int(float(bbox.find('ymin').text))
            xmax = int(float(bbox.find('xmax').text))
            ymax = int(float(bbox.find('ymax').text))

            # 确保坐标在图像范围内
            height, width = image.shape[:2]
            xmin = max(0, xmin)
            ymin = max(0, ymin)
            xmax = min(width, xmax)
            ymax = min(height, ymax)

            # 剪切图像
            cropped = image[ymin:ymax, xmin:xmax]

            # 创建类别子文件夹
            class_folder = os.path.join(output_folder, class_name)
            os.makedirs(class_folder, exist_ok=True)

            # 生成保存文件名
            base_name = os.path.splitext(image_filename)[0]
            save_name = f"{base_name}_{i}.jpg"
            save_path = os.path.join(class_folder, save_name)

            # 保存剪切后的图像
            # cv2.imwrite(save_path, cropped)
            try:
                Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)).save(save_path)
            except:
                pass

if __name__ == "__main__":
    # 使用示例
    xml_folder = Path( "D:\标志\detection_by_image_list1")  # XML标注文件所在文件夹
    image_folder = xml_folder  # 原始图像所在文件夹
    output_folder = xml_folder.parent/"out_crop_image"  # 输出文件夹
    output_folder.mkdir(exist_ok=True,parents=True)
    crop_images_from_xml(str(xml_folder), str(image_folder), str(output_folder))