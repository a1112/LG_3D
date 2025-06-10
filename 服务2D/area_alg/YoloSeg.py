from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO
from PIL import Image

from .YoloModelResults import YoloModelSegResults
from configs import CONFIG


class SteelSegModel:
    def __init__(self):
        self.model = YOLO(str(CONFIG.ModelFolder / "area_seg.pt"))   # load a custom model

    def predict(self, image):
        results = self.model(image)
        res_data = YoloModelSegResults(image,results[0])
        return res_data

