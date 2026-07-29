import json
import threading

import cv2
import numpy as np
from ultralytics import YOLO

from Base import CONFIG
from Base.property.Types import DetectionType
from Base.utils.Log import logger
from .class_name_map import mapped_class_result, normalize_name_map
from .model_memory import release_predictor_input_references


def _predict_static_images(model, predict_lock, source, **kwargs):
    # Clearing predictor state must be serialized with inference. Otherwise a
    # completed caller could clear a second caller's active batch.
    with predict_lock:
        try:
            return model(source, **kwargs)
        finally:
            release_predictor_input_references(model)


def _load_class_name_map():
    config_paths = [
        CONFIG.base_config_folder / "model" / "classifier" / "classifier.json",
        CONFIG.base_config_folder / "model" / "CoilClassifiersConfig.json",
    ]
    for config_path in config_paths:
        if not config_path.exists():
            continue
        try:
            config_data = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            logger.warning("读取分类类别映射失败: %s", e)
            continue
        name_map = normalize_name_map(
            config_data.get("class_name_map",
                            config_data.get("name_map", {})))
        if name_map:
            return name_map
    return {}


class CoilAreaModel:
    def __init__(self):
        self.model = YOLO(str(CONFIG.base_config_folder / "model/CoilArea.pt"), verbose=False)   # load a custom model
        self._predict_lock = threading.Lock()

    def predict(self, image):
        results = _predict_static_images(
            self.model, self._predict_lock, image, verbose=False)
        if results[0].xyxy:
            return results[0].xyxy

    def getSteelRect(self, image):
        results = _predict_static_images(self.model, self._predict_lock, image)
        bounding_boxes = []
        for result in results:
            for box in result.boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                label = int(box.cls[0].cpu().numpy())  # 假设类标签是整数
                xmin, ymin, xmax, ymax = xyxy
                bounding_boxes.append((int(xmin), int(ymin), int(xmax-xmin), int(ymax-ymin),label))
        if bounding_boxes:
            max_rect = max(bounding_boxes, key=lambda x: x[2]*x[3])
            return max_rect
        return []


class CoilMaskModel:
    def __init__(self):
        from ultralytics import YOLO
        self.model = YOLO(str(CONFIG.base_config_folder / "model/CoilSeg.pt"), verbose=False)   # load a custom model
        self._predict_lock = threading.Lock()

    def predict(self, image):
        results = _predict_static_images(
            self.model, self._predict_lock, image, verbose=False)
        if results[0].masks:
            orig_shape = results[0].masks.orig_shape
            mask = results[0].masks.data[0].cpu().numpy()*255
            mask = mask.astype(np.uint8)
            mask = cv2.resize(mask, orig_shape)
            return mask

        return np.zeros_like(image)


class CoilDetectionModel:
    def __init__(self,model_url=None,base_name=None):
        assert model_url is None or base_name is None ,ValueError("设置错误")
        if base_name is not None:
            model_url = str(CONFIG.base_config_folder /"model" /base_name)

        if model_url is None:
            from Globs import control
            if control.detection_model == DetectionType.Detection:
                model_url = str(CONFIG.base_config_folder /"model" /"CoilDetection.pt")
            elif control.detection_model == DetectionType.DetectionAndClassifiers:
                model_url = str(CONFIG.base_config_folder / "model" / "yolo26best.pt")
        logger.info("CoilDetection model is %s", model_url)
        self.model_url = model_url
        self.model = YOLO(model_url, verbose=False)  # load a custom model
        self._predict_lock = threading.Lock()
        self.name_map = _load_class_name_map()
        if self.name_map:
            logger.info("检测模型类别映射: %s", self.name_map)

    def predict(self, images):
        if not images:
            logger.warning("skip detection model predict: empty image list")
            return []
        results = _predict_static_images(
            self.model, self._predict_lock, images, verbose=False)
        res_list = []
        for result in results:
            res_item_list = []
            for box in result.boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                label_index = int(box.cls[0].cpu().numpy())
                name = self.model.names[label_index]
                label_index, name = mapped_class_result(
                    label_index, name, self.model.names, self.name_map)
                xmin, ymin, xmax, ymax = xyxy
                source = float(box.conf[0].cpu().numpy())
                res_item_list.append((int(xmin), int(ymin), int(xmax), int(ymax), label_index, source,name))
            res_list.append(res_item_list)
        return res_list

