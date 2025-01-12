import os
import shutil
import random
import socket
from pathlib import Path


def create_yolo_dataset_structure(base_path):
    structure = [
        'images/train',
        'images/val',
        'labels/train',
        'labels/val'
    ]
    for folder in structure:
        path = os.path.join(base_path, folder)
        if not os.path.exists(path):
            os.makedirs(path)
    print(f"Created YOLO dataset structure at {base_path}")



def organize_yolo_dataset(image_folder, label_folder, output_folder, train_ratio=0.8):
    create_yolo_dataset_structure(output_folder)

    # 获取所有图像文件
    image_files = [f for f in os.listdir(image_folder) if f.endswith('.jpg') or f.endswith('.png')]

    # 随机打乱图像文件列表
    random.shuffle(image_files)

    # 分割训练集和验证集
    train_size = int(len(image_files) * train_ratio)
    train_files = image_files[:train_size]
    val_files = image_files[train_size:]

    def copy_files(file_list, subset):
        for image_file in file_list:
            base_name = os.path.splitext(image_file)[0]
            image_path = os.path.join(image_folder, image_file)
            label_path = os.path.join(label_folder, base_name + '.txt')

            if os.path.exists(label_path):
                image_dest = os.path.join(output_folder, 'images', subset, image_file)
                label_dest = os.path.join(output_folder, 'labels', subset, base_name + '.txt')

                shutil.copy(image_path, image_dest)
                shutil.copy(label_path, label_dest)

    # 处理训练集
    copy_files(train_files, 'train')
    # 处理验证集
    copy_files(val_files, 'val')

    print(f"Organized YOLO dataset in {output_folder}")


print(socket.gethostname())

if socket.gethostname() == "lcx_ace":
    # 示例使用
    # 示例使用
    image_folder = Path(r'F:\subImage\样本_合并')  # 包含图像文件的文件夹
    label_folder = image_folder.parent / "txt"  # 包含YOLO格式标注文件的文件夹
    output_folder = label_folder.parent / "Dataset"  # 用于保存组织后的数据集的文件夹
    output_folder.mkdir(parents=True, exist_ok=True)
    organize_yolo_dataset(image_folder, label_folder, output_folder)