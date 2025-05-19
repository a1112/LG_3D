import os
import xml.etree.ElementTree as ET
from PIL import Image


def convert_voc_coords_to_percent(folder_path):
    # 遍历文件夹内所有XML文件
    for xml_file in os.listdir(folder_path):
        if not xml_file.lower().endswith('.xml'):
            continue

        xml_path = os.path.join(folder_path, xml_file)

        # 获取对应的jpg路径
        jpg_path = os.path.splitext(xml_path)[0] + '.png'
        if not os.path.exists(jpg_path):
            print(f"警告：未找到对应的图片文件 {jpg_path}，跳过处理")
            continue

        try:
            # 获取图片尺寸
            with Image.open(jpg_path) as img:
                img_width, img_height = img.size

            # 解析XML
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # 遍历所有目标框
            for obj in root.findall('object'):
                bndbox = obj.find('bndbox')
                if bndbox is None:
                    continue

                # 提取原始坐标
                xmin = float(bndbox.find('xmin').text)
                ymin = float(bndbox.find('ymin').text)
                xmax = float(bndbox.find('xmax').text)
                ymax = float(bndbox.find('ymax').text)

                # 计算百分比坐标（0-1范围）
                xmin_pct = int(xmin % img_height)
                ymin_pct = int(ymin % img_width)
                xmax_pct = int(xmax % img_height)
                ymax_pct = int(ymax % img_width)

                # 更新坐标值
                bndbox.find('xmin').text = str(xmin_pct)
                bndbox.find('ymin').text = str(ymin_pct)
                bndbox.find('xmax').text = str(xmax_pct)
                bndbox.find('ymax').text = str(ymax_pct)

            # 保存修改后的XML（保留XML声明）
            tree.write(xml_path, encoding='UTF-8', xml_declaration=True)
            print(f"已处理文件：{xml_file}")

        except Exception as e:
            print(f"处理文件 {xml_file} 时出错：{str(e)}")


if __name__ == "__main__":
    folder_path = fr"D:\标志\标记05"
    convert_voc_coords_to_percent(folder_path)