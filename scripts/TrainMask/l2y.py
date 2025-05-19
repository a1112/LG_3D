#  seg 模式

from labelme2yolov8.l2y import Labelme2YOLOv8


Labelme2YOLOv8(
    fr'G:\TRAIN\AreaSaveFolder\data',
    "polygon",
    ["coil"]
).convert(0.1,0.1)