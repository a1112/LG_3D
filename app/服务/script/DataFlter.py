from multiprocessing import freeze_support

import AlarmDetection
import AlarmDetection.detection
from property.Base import DataIntegrationList
from utils.LoggerProcess import LoggerProcess

if __name__ == '__main__':
    freeze_support()
    from SplicingService.ImageMosaic import ImageMosaic
    from SplicingService.DataFolder import DataFolder
    from SplicingService.ImageMosaicThread import ImageMosaicThread
    imageMosaicThrea=ImageMosaicThread(None,LoggerProcess())
    # imageMosaicThrea.start()
    from PIL import Image
    for i in range(35074, 35079):
        dataIntegrationList = DataIntegrationList()
        for mosaic in imageMosaicThrea.imageMosaicList[::-1]:
            # mosaic.setSave(True)
            mosaic.set_coil_id(i)
            dataIntegration = mosaic.get_data()
            dataIntegrationList.append(dataIntegration)  # 检测
        AlarmDetection.detection.detection_all(dataIntegrationList)
        # cv_detection.detectionAll(dataIntegrationList)
    # mosaic.maskImage.show()
    # mosaic.maskImage.show()
    # Image.fromarray(mosaic.jetImage).show()
    # mosaic.grayImage.show()
