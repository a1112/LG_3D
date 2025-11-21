import socket

from Base.CONFIG import controlConfigFile, controlConfigProperty
from Base.property.ControlProperty import ControlProperty
from Base.property.Types import DetectionTaperShapeType, LevelingType, DetectionType, GetFileTypeJpg
from Base.property.WorkerBase import WorkerThreadBase, WorkerProcessBase

ThreadClass = WorkerThreadBase
ProcessClass = WorkerThreadBase # WorkerProcessBase


class ControlManagement(ThreadClass):
    ThreadClass = ThreadClass
    ProcessClass = ThreadClass

    def __init__(self):
        super().__init__()
        self.config = controlConfigProperty.config
        self.configFile = controlConfigFile
        self.ImageSaverWorkNum = 2
        self.minMaskDetectErrorSize = 2000  # mask 检测最小报警值
        self.median_filter_size = 5
        self.downsampleSize = 7  # 如果下采样 1，数据将会非常庞大
        self.BaseImageMosaic = ThreadClass
        self.ImageSaverThreadType = "ThreadClass" # multiprocessing
        self.D3SaverWorkNum = 3
        self.D3SaverThreadType = "ThreadClass"  # multiprocessing
        self.D3SaverThreadMaxsize = 5
        self.ImageSaverQueueSize = 5
        self.BaseDataFolder = ProcessClass
        self.baseTimeFormat = "%Y-%m-%d %H:%M:%S"
        self.exportTimeFormat = self.baseTimeFormat
        self.logTimeFormat = self.baseTimeFormat
        self.upper_limit = 75
        self.lower_limit = -75
        self.leveling_gray = True
        self.leveling_3d = True
        self.leveling_type = LevelingType.LinearRegression
        self.taper_shape_type = DetectionTaperShapeType.LINE_TYPE
        self.leveling_3d_wk_default_value = 32767
        self.save_3d_obj = True
        self.debug_show = False
        self.debug_raise = False
        self.save_detection = True  #保存目标检测小图
        self.save_sub_image = True
        self.SaveAndDeleteCameraDataBase = ProcessClass
        self.SaveAndDeleteSaveDataBase = ProcessClass

        self.detection_model = DetectionType.DetectionAndClassifiers

        self.get_file_type = GetFileTypeJpg

        self.out_side_px = 0 #  拓展 像素
        self.loc_sleep_time = 5
        hostname = socket.gethostname()
        if hostname=="DESKTOP-94ADH1G":
            self.ImageSaverWorkNum = 1
            self.median_filter_size = 7
            self.D3SaverWorkNum = 1
            self.D3SaverThreadMaxsize = 1
            self.ImageSaverThreadType = "Thread"
            self.loc_sleep_time = 100
        self.start()

    def get(self):
        return ControlProperty(self.config)

    def get_config(self):
        return self.config

    def set_config(self, data):
        self.config.update(data)

    def set_property(self, key, value):
        self.config[key] = value

    def run(self):
        pass
