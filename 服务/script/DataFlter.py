from multiprocessing import freeze_support

if __name__ == '__main__':
    freeze_support()

from SplicingService.ImageMosaic import ImageMosaic
from SplicingService.DataFolder import DataFolder
from SplicingService.main import ImageMosaicThread
imageMosaicThrea=ImageMosaicThread(None)
imageMosaicThrea.start()
from PIL import Image
for mosaic in imageMosaicThrea.imageMosaicList[::-1]:
    for i in range(23167,23169):
        try:
            mosaic.setSave(True)
            mosaic.setCoilId(i)
            mosaic.getJoinImage()
        except BaseException:
            pass

# mosaic.maskImage.show()
# mosaic.maskImage.show()
# Image.fromarray(mosaic.jetImage).show()
# mosaic.grayImage.show()
input()
