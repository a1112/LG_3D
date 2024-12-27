import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
# 配置路径
VOC_ROOT = Path('D:\样本\中间增加\原训练集')  # VOC 数据集根目录
ANNOTATIONS_DIR = os.path.join(VOC_ROOT, 'image')
JPEGIMAGES_DIR = os.path.join(VOC_ROOT, 'imagerar.')
OUTPUT_DIR = os.path.join(VOC_ROOT, 'Sorted')  # 输出目录

# 创建输出目录
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 遍历所有 XML 文件
for xml_file in os.listdir(ANNOTATIONS_DIR):
    if not xml_file.endswith('.xml'):
        continue

    xml_path = os.path.join(ANNOTATIONS_DIR, xml_file)

    # 解析 XML
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # 获取第一个标签的名称
    first_object = root.find('object')
    if first_object is None:
        print(f"文件 {xml_file} 中没有对象标签，跳过。")
        label = "None"
    else:
        label = first_object.find('name').text.strip()
    if not label:
        print(f"文件 {xml_file} 的第一个标签名称为空，跳过。")
        continue

    # 创建标签对应的文件夹
    label_dir = os.path.join(OUTPUT_DIR, label)
    os.makedirs(label_dir, exist_ok=True)

    # 获取图片文件名
    filename = Path(xml_file).with_suffix(".png").name
    image_path = os.path.join(JPEGIMAGES_DIR, filename)

    if not os.path.exists(image_path):
        print(f"对应的图片文件 {filename} 不存在，跳过。")
        continue

    # 复制图片和 XML 文件到标签文件夹
    shutil.copy(image_path, label_dir)
    shutil.copy(xml_path, label_dir)

    print(f"已将 {filename} 和 {xml_file} 复制到 {label_dir}")

print("拆分完成。")
