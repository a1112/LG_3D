import numpy as np
from ultralytics import YOLO
from PIL import Image
from pathlib import Path
import CONFIG
import cv2


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
            maxRect = max(bounding_boxes, key=lambda x: x[2]*x[3])
            return maxRect
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
    def __init__(self):

        self.model = YOLO(str(CONFIG.base_config_folder / "model/CoilDetection.pt"))  # load a custom model

    def predict(self, images):
        results = self.model(images)
        resList = []
        for result in results:
            resItemList = []
            for box in result.boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                labelIndex = int(box.cls[0].cpu().numpy())
                name = self.model.names[labelIndex]
                xmin, ymin, xmax, ymax = xyxy
                source = float(box.conf[0].cpu().numpy())
                resItemList.append((int(xmin), int(ymin), int(xmax), int(ymax), labelIndex, source,name))
            resList.append(resItemList)
        return resList
