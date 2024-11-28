import json
from pathlib import Path
import numpy as np
from PIL import Image
import os
import cv2
from labelme import utils
from tqdm import tqdm


def create_labelme_json(image_path, mask_path, output_path, epsilon_factor=0.0015):
    image = Image.open(image_path)
    mask = Image.open(mask_path)

    image_np = np.array(image)
    mask_np = np.array(mask)

    # 找到轮廓
    contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    shapes = []
    for contour in contours:
        # 使用 Ramer-Douglas-Peucker 算法简化轮廓
        epsilon = epsilon_factor * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        points = approx.squeeze().tolist()
        shape = {
            'label': 'object',
            'points': points,
            'group_id': None,
            'shape_type': 'polygon',
            'flags': {}
        }
        shapes.append(shape)

    # 创建 LabelMe 格式的 JSON 数据
    data = {
        'version': '4.5.6',  # 版本号
        'flags': {},
        'shapes': shapes,
        'imagePath': os.path.basename(image_path),
        'imageData': utils.img_arr_to_b64(image_np),
        'imageHeight': image_np.shape[0],
        'imageWidth': image_np.shape[1]
    }

    # 保存为 JSON 文件
    json_path = os.path.join(output_path, os.path.splitext(os.path.basename(image_path))[0] + '.json')
    with open(json_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)


# 示例用法
image_dir = Path(r'F:\ALG\SegTrainTest\trainTest\dataList\cropMask\pre\mask')
output_dir = image_dir.parent / 'json'
output_dir.mkdir(parents=True, exist_ok=True)

for file_name in tqdm(image_dir.glob('*.png')):
    image_path = file_name.parent.parent / "image" / file_name.name
    mask_path = file_name
    create_labelme_json(image_path, mask_path, output_dir)

