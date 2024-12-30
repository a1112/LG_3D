import cv2
import numpy as np
from ultralytics import YOLO

import CONFIG
from property.Types import DetectionType


class CoilAreaModel:
    def __init__(self):
        from ultralytics import YOLO
        self.model = YOLO(str(CONFIG.base_config_folder / "model/CoilArea.pt"))   # load a custom model

    def predict(self, image):
        results = self.model(image)
        if results[0].xyxy:
            return results[0].xyxy

    def getSteelRect(self, image):
        results = self.model(image)
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
        self.model = YOLO(str(CONFIG.base_config_folder / "model/CoilSeg.pt"))   # load a custom model

    def predict(self, image):
        results = self.model(image)
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
                model_url = str(CONFIG.base_config_folder / "model" / "CoilDetection_JC.pt")
        print(model_url)
        self.model_url = model_url
        self.model = YOLO(model_url)  # load a custom model

    def predict(self, images):
        results = self.model(images)
        res_list = []
        for result in results:
            res_item_list = []
            for box in result.boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                label_index = int(box.cls[0].cpu().numpy())
                name = self.model.names[label_index]
                xmin, ymin, xmax, ymax = xyxy
                source = float(box.conf[0].cpu().numpy())
                res_item_list.append((int(xmin), int(ymin), int(xmax), int(ymax), label_index, source,name))
            res_list.append(res_item_list)
        return res_list

