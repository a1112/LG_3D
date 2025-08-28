from pathlib import Path
from queue import Queue

from threading import Thread
from typing import List

import numpy as np
from PIL import Image
from lxml import etree
from property.DataIntegration import DataIntegration, ClipImageItem
from configs import CONFIG
from ultralytics import YOLO

class DetectionSave(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.debug_save_folder = CONFIG.base_debug_image_save_folder
        if CONFIG.DEBUG:
            self.debug_save_folder.mkdir(parents=True, exist_ok=True)
        self.queue = Queue(maxsize=20)
        self.start()

    def add(self,image,url):
        self.queue.put([image,url])

    def run(self):
        while True:
            try:
                item = self.queue.get()
                image, url = item
                if isinstance(image, Image.Image):
                    image = image
                if isinstance(image,np.ndarray):
                    image=Image.fromarray(image)
                image.save(url)
            except:
                pass



detect_save = DetectionSave()


def create_xml(file_name, img_shape, bounding_boxes, output_folder):
    annotation = etree.Element("annotation")

    folder = etree.SubElement(annotation, "folder")
    folder.text = "images"

    filename = etree.SubElement(annotation, "filename")
    filename.text = str(file_name)

    size = etree.SubElement(annotation, "size")
    width = etree.SubElement(size, "width")
    width.text = str(img_shape[1])
    height = etree.SubElement(size, "height")
    height.text = str(img_shape[0])
    depth = etree.SubElement(size, "depth")
    depth.text = str(img_shape[2])

    for bbox in bounding_boxes:
        bbox:CoilDetectionResult

        xmin, ymin, xmax, ymax,label = bbox.xmin, bbox.ymin, bbox.xmax, bbox.ymax, bbox.label
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
    print(xml_path)
    tree.write(str(xml_path), pretty_print=True, xml_declaration=True, encoding="utf-8")
    print(f"Saved XML to {xml_path}")

class CoilDetectionResult:
    def __init__(self,xmin, ymin, xmax, ymax, label,source,name,image):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        self.label = label
        self.source = source
        self.name = name
        self.image = image
        self.key = fr"{self.name}_{self.source}_{self.label}"


    def get_image(self):
        return self.image[self.ymin:self.ymax,self.xmin:self.xmax]


class YoloResult:
    def __init__(self,image_info:ClipImageItem, info_list:List[CoilDetectionResult]):
        self.image_info = image_info
        self.info_list = info_list

        self.file_name = image_info.get_file_name()
        self.image=image_info.image
        self.debug_save_folder = CONFIG.base_debug_image_save_folder
        if self.has_det():
            self.save_det()

    def save_det(self):
        save_jpg=self.debug_save_folder/"det"/self.file_name
        save_jpg.with_suffix(".jpg")
        save_jpg.parent.mkdir(parents=True, exist_ok=True)
        create_xml(save_jpg.name, self.image_info.image.shape, self.info_list, save_jpg.parent)
        detect_save.add(self.image, save_jpg)

    def has_det(self):
        return bool(self.info_list)

class CoilDetectionModel:
    def __init__(self,model_url=None,base_name=None):
        model_url = str(CONFIG.base_config_folder / "model" / "CoilDetection_Area_JC.pt")
        print(fr" CoilDetection model is {model_url}")
        self.model_url = model_url
        self.model = YOLO(model_url)  # load a custom model

    def predict(self,item_info: ClipImageItem):
        results = self.model(item_info.image)
        res_list = []
        if not isinstance(item_info, list):
            item_info = [item_info]

        for result,image in zip(results,item_info):
            res_item_list = []
            for box in result.boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                label_index = int(box.cls[0].cpu().numpy())
                name = self.model.names[label_index]
                xmin, ymin, xmax, ymax = xyxy
                source = float(box.conf[0].cpu().numpy())
                res_item_list.append(CoilDetectionResult(int(xmin), int(ymin), int(xmax), int(ymax), label_index, source,name,image))
            res_list.append(YoloResult(image,res_item_list))
        return res_list


coil_detection_model = CoilDetectionModel()

from CoilDataBase.models.CoilDefect import CoilDefect
from CoilDataBase.Coil import add_defects
def add_db(det_info):
    defect_list=[]
    for item in det_info:
        item: YoloResult
        for defect_item in item.info_list:
            defect_item:CoilDetectionResult
            clip_image_item = item.image_info
            clip_image_item:ClipImageItem
            defect_list.append({
            "secondaryCoilId": clip_image_item.coil_id,
            "surface": clip_image_item.surface,
            "defectClass": 101,
            "defectName": "2D_检出",
            "defectStatus": 5,
            "defectX": clip_image_item.box[0]+defect_item.xmin,
            "defectY": clip_image_item.box[1]+defect_item.ymin,
            "defectW": clip_image_item.box[2]+defect_item.xmin,
            "defectH":clip_image_item.box[3]+defect_item.ymin,
            "defectSource": clip_image_item.source,
            "defectData": "",
            })
    print(fr"添加检测数据 {defect_list}")
    add_defects(defect_list)


def detection(data_integration: DataIntegration):

    """
    数据检测
    """

    clip_image_list = data_integration.clip_image()
    for item in clip_image_list:
        item: ClipImageItem
        det_info = coil_detection_model.predict(item)
        add_db(det_info)





