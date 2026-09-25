import os
from threading import Lock
from typing import List

from ultralytics import YOLO

from algorithm_runtime_2D.utils.DetectionSpeedRecord import DetectionSpeedRecord
from algorithm_runtime_2D.utils.model_memory import release_predictor_input_references
from .YoloModelResults import YoloModelSegResults
from algorithm_runtime_2D.configs import CONFIG


class SteelSegModel:
    def __init__(self):
        self.model = YOLO(str(CONFIG.ModelFolder / "area_seg.pt"))   # load a custom model
        self._model_lock = Lock()

    @DetectionSpeedRecord.timing_decorator("单张图像预测 ")
    def predict_one(self, image):
        return self.predict(image)[0]

    @DetectionSpeedRecord.timing_decorator("图像预测 ")
    def predict(self, image_list,batch_size=None)->List[YoloModelSegResults]:
        if not isinstance(image_list, (list, tuple)):
            image_list = [image_list]
        if batch_size is None:
            batch_size = os.getenv("ALG_2D_YOLO_BATCH_SIZE", "2")
        try:
            batch_size = max(int(batch_size), 1)
        except (TypeError, ValueError):
            batch_size = 2

        if len(image_list)==0:
            return []

        res_data = []
        for start in range(0, len(image_list), batch_size):
            batch = image_list[start:start + batch_size]
            with self._model_lock:
                try:
                    results = self.model(batch, verbose=False)
                finally:
                    # The returned list remains valid; this only removes the
                    # predictor's duplicate ownership of the completed batch.
                    release_predictor_input_references(self.model)
            res_data.extend(YoloModelSegResults(image, result) for image, result in zip(batch, results))
        return res_data
