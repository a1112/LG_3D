from threading import *
import cv2
from tqdm import tqdm
from BKVisionCamera import crate_capter, CaptureModel, HikCamera

class Captrue(Thread):
    def __init__(self, yaml=r"../demo/Area_S_D.yaml"):
        super().__init__()
        self.yaml=yaml
        self.capter = crate_capter(self.yaml)  # 创建 CapTrue 模型

    def run(self):
        pass

        with capter as cap:
            cap: HikCamera
            i = 0
            while i < 10000000:
                frame = cap.getFrame()
                i += 1
                tq.update(1)
                print(frame)
                if frame is None:
                    break
                cv2.imshow("frame", frame)
                cv2.waitKey(1)