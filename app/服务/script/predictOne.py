import socket
from pathlib import Path
import concurrent.futures

from alg import detection
from alg.CoilMaskModel import CoilDetectionModel

cdm = CoilDetectionModel(base_name="CoilDetection_JC.pt")

res = cdm.predict(r"E:\train\train\Dataset\images\train\35550_S_4540_4500_590_585.png")
print(res)
