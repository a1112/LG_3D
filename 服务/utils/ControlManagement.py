from CONFIG import controlConfig, controlConfigFile
from property.ControlProperty import ControlProperty
from property.Types import DetectionTaperShapeType, LevelingType, DetectionType, GetFileTypeJpg
from property.WorkerBase import WorkerThreadBase, WorkerProcessBase

ThreadClass = WorkerThreadBase
ProcessClass = WorkerProcessBase


class ControlManagement(ThreadClass):
    ThreadClass = ThreadClass
    ProcessClass = ThreadClass

    def __init__(self):
        super().__init__()
        self.config = controlConfig
        self.configFile = controlConfigFile
        self.ImageSaverWorkNum = 3
        self.minMaskDetectErrorSize = 2000  # mask 检测最小报警值
        self.median_filter_size = 3
        self.downsampleSize = 3  # 如果下采样 1，数据将会非常庞大
        self.BaseImageMosaic = ThreadClass
        self.ImageSaverThreadType = "multiprocessing"
        self.D3SaverWorkNum = 10
        self.D3SaverThreadType = "multiprocessing"
        self.D3SaverThreadMaxsize = 5
        self.ImageSaverQueueSize = 20
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

        self.SaveAndDeleteCameraDataBase = ProcessClass
        self.SaveAndDeleteSaveDataBase = ProcessClass

        self.detection_model = DetectionType.DetectionAndClassifiers

        self.get_file_type = GetFileTypeJpg

        self.start()

    def get(self):
        return ControlProperty(self.config)

    def get_config(self):
        return self.config

    def setConfig(self, data):
        self.config.update(data)

    def set_property(self, key, value):
        self.config[key] = value

    def run(self):
        pass
