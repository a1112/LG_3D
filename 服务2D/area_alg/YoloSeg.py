from pathlib import Path
from typing import List

import cv2
import numpy as np
from ultralytics import YOLO
from PIL import Image

from utils.DetectionSpeedRecord import DetectionSpeedRecord
from .YoloModelResults import YoloModelSegResults
from configs import CONFIG


class SteelSegModel:
    def __init__(self):
        self.model = YOLO(str(CONFIG.ModelFolder / "area_seg.pt"))   # load a custom model

    @DetectionSpeedRecord.timing_decorator("单张图像预测 ")
    def predict_one(self, image):
        return self.predict(image)[0]

    @DetectionSpeedRecord.timing_decorator("图像预测 ")
    def predict(self, image_list,batch_size=16)->List[YoloModelSegResults]:

        if len(image_list)==0:
            return []
        if len(image_list)>batch_size:
            return self.predict(image_list[:batch_size])+self.predict(image_list[batch_size:])

        results = self.model(image_list)
        res_data = [YoloModelSegResults(image,result) for image, result in zip(image_list,results)]
        return res_data