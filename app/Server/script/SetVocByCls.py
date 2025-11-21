import tqdm

from alg.CoilClsModel import CoilClsModel
from pathlib import Path
from PIL import Image
import os
import shutil
import xml.etree.ElementTree as ET
from CONFIG import coilClassifiersConfigFile

voc_folder=Path(fr"E:\detection_by_image_list")
image_folder = voc_folder
save_to_folder = voc_folder.parent/"cls_to_voc"
save_to_folder_sub_image = voc_folder.parent/"cls_to_voc_sub_image"
# 使用示例
objects = []
sub_images=[]

for xml_url in tqdm.tqdm(voc_folder.glob("*.xml")):
    image_url = image_folder/xml_url.with_suffix(".png").name
    if not image_url.exists():
        continue
    image = Image.open(image_url)
    tree = ET.parse(xml_url)
    root = tree.getroot()
    for obj in root.findall('object'):
        obj_name = obj.find('name').text
        x_min = int(obj.find('bndbox').find('xmin').text)
        y_min = int(obj.find('bndbox').find('ymin').text)
        xmax = int(obj.find('bndbox').find('xmax').text)
        ymax = int(obj.find('bndbox').find('ymax').text)
        objects.append([x_min, y_min, xmax, ymax, obj_name])
        sub_images.append(image.crop((x_min, y_min, xmax, ymax)))
    # if len(sub_images)>100:
    #     break

model = CoilClsModel(config=coilClassifiersConfigFile)
res_index,res_source,names = model.predict_image(sub_images)

zip_data=zip(objects,res_index,res_source,names,sub_images)
for xml_url in tqdm.tqdm(voc_folder.glob("*.xml")):
    xml_url=Path(xml_url)
    image_url = image_folder/xml_url.with_suffix(".png").name
    if not image_url.exists():
        continue
    tree = ET.parse(xml_url)
    root = tree.getroot()
    name_="None"
    for obj in root.findall('object'):
        xml,cls_index,source,name,sub_img=next(zip_data)
        name_=name
        name_elem = ET.SubElement(obj, 'name')
        name_elem.text = name
        bndbox = ET.SubElement(obj, 'bndbox')
        xmin_elem = ET.SubElement(bndbox, 'xmin')
        xmin_elem.text = str(xml[0])
        ymin_elem = ET.SubElement(bndbox, 'ymin')
        ymin_elem.text = str(xml[1])
        xmax_elem = ET.SubElement(bndbox, 'xmax')
        xmax_elem.text = str(xml[2])
        ymax_elem = ET.SubElement(bndbox, 'ymax')
        ymax_elem.text = str(xml[3])
        sab_image_save_folder = save_to_folder_sub_image/name_
        sab_image_save_folder.mkdir(exist_ok=True, parents=True)
        sub_img.save(sab_image_save_folder/(xml_url.stem+fr"{xml[0]}_{xml[1]}_{xml[2]}_{xml[3]}_{xml[4]}.png"))

    save_folder=save_to_folder/name_
    save_folder.mkdir(exist_ok=True,parents=True)
    xml_path = save_folder/xml_url.with_suffix(".xml").name
    tree.write(str(xml_path), xml_declaration=True, encoding="utf-8")
    shutil.copy(image_url,save_folder/image_url.name)