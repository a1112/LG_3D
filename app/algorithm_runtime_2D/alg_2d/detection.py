from pathlib import Path
from queue import Queue
from threading import Thread
from typing import List

import numpy as np
from lxml import etree
from PIL import Image
from ultralytics import YOLO

from CoilDataBase.Coil import add_defects, replace_defects
from alg_2d.classifier import (AREA_DEFECT_NAME_PREFIX,
                               DEFAULT_2D_DEFECT_CLASS, area_defect_name,
                               classify_boxes)
from configs import CONFIG
from property.DataIntegration import ClipImageItem, DataIntegration
from utils.MultiprocessColorLogger import logger


class DetectionSave(Thread):

    def __init__(self):
        Thread.__init__(self)
        self.debug_save_folder = CONFIG.base_debug_image_save_folder
        if CONFIG.DEBUG:
            self.debug_save_folder.mkdir(parents=True, exist_ok=True)
        self.queue = Queue(maxsize=20)
        self.start()

    def add(self, image, url) -> None:
        self.queue.put([image, url])

    def run(self) -> None:
        while True:
            try:
                item = self.queue.get()
                image, url = item
                if isinstance(image, np.ndarray):
                    image = Image.fromarray(image)
                image.save(url)
            except Exception as e:
                logger.exception("DetectionSave save failed: %s", e)


detect_save = DetectionSave()


def create_xml(file_name, img_shape, bounding_boxes, output_folder) -> None:
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
        bbox: CoilDetectionResult
        xmin, ymin, xmax, ymax, label = bbox.xmin, bbox.ymin, bbox.xmax, bbox.ymax, bbox.label
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
    xml_path = Path(output_folder) / (Path(file_name).stem + ".xml")
    tree.write(str(xml_path),
               pretty_print=True,
               xml_declaration=True,
               encoding="utf-8")
    logger.debug("Saved XML to %s", xml_path)


class CoilDetectionResult:

    def __init__(self, xmin, ymin, xmax, ymax, label, source, name, image):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        self.label = label
        self.source = source
        self.name = name
        self.image = image
        self.is_classified = False
        self.key = fr"{self.name}_{self.source}_{self.label}"

    def get_image(self):
        return self.image[self.ymin:self.ymax, self.xmin:self.xmax]

    def set_classification(self, label: int, source: float, name: str) -> None:
        self.label = label
        self.source = source
        self.name = name
        self.is_classified = True
        self.key = fr"{self.name}_{self.source}_{self.label}"


class YoloResult:

    def __init__(self, image_info: ClipImageItem,
                 info_list: List[CoilDetectionResult]):
        self.image_info = image_info
        self.info_list = info_list

        self.file_name = image_info.get_file_name()
        self.image = image_info.image
        self.debug_save_folder = CONFIG.base_debug_image_save_folder
        if self.has_det():
            self.save_det()

    def save_det(self) -> None:
        save_jpg = (self.debug_save_folder / "det" /
                    self.file_name).with_suffix(".jpg")
        save_jpg.parent.mkdir(parents=True, exist_ok=True)
        create_xml(save_jpg.name, self.image_info.image.shape, self.info_list,
                   save_jpg.parent)
        detect_save.add(self.image, save_jpg)

    def has_det(self) -> bool:
        return bool(self.info_list)


class CoilDetectionModel:

    def __init__(self, model_url=None, base_name=None):
        model_url = str(CONFIG.base_config_folder / "model" /
                        "CoilDetection_Area_JC.pt")
        logger.info("CoilDetection model is %s", model_url)
        self.model_url = model_url
        self.model = YOLO(model_url)

    def predict(self, item_info: ClipImageItem):
        results = self.model(item_info.image, imgsz=CONFIG.area_detection_image_size)
        res_list = []
        if not isinstance(item_info, list):
            item_info = [item_info]

        for result, image in zip(results, item_info):
            res_item_list = []
            for box in result.boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                label_index = int(box.cls[0].cpu().numpy())
                name = self.model.names[label_index]
                xmin, ymin, xmax, ymax = xyxy
                source = float(box.conf[0].cpu().numpy())
                res_item_list.append(
                    CoilDetectionResult(int(xmin), int(ymin), int(xmax),
                                        int(ymax), label_index, source, name,
                                        image))
            res_list.append(YoloResult(image, res_item_list))
        return res_list


coil_detection_model = CoilDetectionModel()


def _get_absolute_defect_box(
        clip_image_item: ClipImageItem,
        defect_item: CoilDetectionResult) -> tuple[int, int, int, int] | None:
    clip_x1, clip_y1, clip_x2, clip_y2 = clip_image_item.box
    defect_x1 = min(max(clip_x1 + defect_item.xmin, clip_x1), clip_x2)
    defect_y1 = min(max(clip_y1 + defect_item.ymin, clip_y1), clip_y2)
    defect_x2 = min(max(clip_x1 + defect_item.xmax, clip_x1), clip_x2)
    defect_y2 = min(max(clip_y1 + defect_item.ymax, clip_y1), clip_y2)
    if defect_x2 <= defect_x1 or defect_y2 <= defect_y1:
        return None
    return (
        int(defect_x1),
        int(defect_y1),
        int(defect_x2 - defect_x1),
        int(defect_y2 - defect_y1),
    )


def apply_classifier(det_info: List[YoloResult], source_image) -> None:
    defect_items = []
    defect_boxes = []
    for item in det_info:
        item: YoloResult
        for defect_item in item.info_list:
            defect_item: CoilDetectionResult
            defect_box = _get_absolute_defect_box(item.image_info, defect_item)
            if defect_box is None:
                continue
            defect_items.append(defect_item)
            defect_boxes.append(defect_box)

    for defect_item, result in zip(defect_items,
                                   classify_boxes(source_image, defect_boxes)):
        if result is not None:
            defect_item.set_classification(result.label, result.source,
                                           result.name)


def build_defect_list(det_info: List[YoloResult]) -> List[dict]:
    defect_list = []
    for item in det_info:
        item: YoloResult
        for defect_item in item.info_list:
            defect_item: CoilDetectionResult
            clip_image_item = item.image_info
            clip_image_item: ClipImageItem
            defect_box = _get_absolute_defect_box(clip_image_item, defect_item)
            if defect_box is None:
                continue
            defect_x, defect_y, defect_w, defect_h = defect_box
            defect_list.append({
                "secondaryCoilId": clip_image_item.coil_id,
                "surface": clip_image_item.surface,
                "defectClass": defect_item.label
                if defect_item.is_classified else DEFAULT_2D_DEFECT_CLASS,
                "defectName": area_defect_name(defect_item.name),
                "defectStatus": 5,
                "defectX": defect_x,
                "defectY": defect_y,
                "defectW": defect_w,
                "defectH": defect_h,
                "defectSource": defect_item.source,
                "defectData": "",
            })
    return defect_list


def add_db(det_info: List[YoloResult]) -> None:
    defect_list = build_defect_list(det_info)
    add_defects(defect_list)


def detection(data_integration: DataIntegration) -> None:
    clip_image_list = data_integration.clip_image()
    det_info_list = []
    for item in clip_image_list:
        item: ClipImageItem
        det_info = coil_detection_model.predict(item)
        det_info_list.extend(det_info)
    apply_classifier(det_info_list, data_integration.max_image)
    if CONFIG.add_to_database:
        defect_list = build_defect_list(det_info_list)
        replace_defects(defect_list, data_integration.coil_id,
                        data_integration.config.surface_key,
                        AREA_DEFECT_NAME_PREFIX)
