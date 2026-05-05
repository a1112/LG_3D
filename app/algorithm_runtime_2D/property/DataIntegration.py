import cv2

from JoinService.cv_count_tool import im_show
from configs import CONFIG
from configs.SurfaceConfig import SurfaceConfig


class ClipImageItem:

    def __init__(self,coil_id,surface_key,image,box):
        self.coil_id = coil_id
        self.surface_key = surface_key
        self.surface = surface_key
        self.image = image
        self.box = box

    def show(self):

        return im_show(self.image,str(self.box))

    def get_file_name(self):
        return f"{self.coil_id}_{self.surface_key}_"+"_".join([str(b) for b in self.box])+".png"

class DataIntegration:

    def __init__(self, config:SurfaceConfig,coil_id):
        self.coil_id = coil_id
        self.config = config
        self.max_image = None
        self.image_width = None
        self.image_height = None
        self.clip_size = CONFIG.area_detection_tile_size
        self.clip_number = 0
        self.x_starts = []
        self.y_starts = []
        self.item_width = None
        self.item_height = None


    def set_max_image(self, max_image):
        if isinstance(max_image, str):
            max_image = cv2.imread(max_image)
        self.max_image = max_image
        self.image_width = max_image.shape[1]
        self.image_height = max_image.shape[0]
        self.x_starts = list(range(0, self.image_width, self.clip_size)) or [0]
        self.y_starts = list(range(0, self.image_height, self.clip_size)) or [0]
        self.clip_number = max(len(self.x_starts), len(self.y_starts))
        self.item_width = self.clip_size
        self.item_height = self.clip_size

    def _pad_clip_image(self, clip_image):
        h, w = clip_image.shape[:2]
        pad_bottom = self.clip_size - h
        pad_right = self.clip_size - w
        if pad_bottom <= 0 and pad_right <= 0:
            return clip_image

        return cv2.copyMakeBorder(
            clip_image,
            0,
            max(0, pad_bottom),
            0,
            max(0, pad_right),
            cv2.BORDER_CONSTANT,
            value=(0, 0, 0),
        )

    def clip_image(self):
        """
        将图像拆封为 n*n 块
        """
        item_image_list=[]
        for left in self.x_starts:
            for top in self.y_starts:
                right = min(left + self.item_width, self.image_width)
                bottom = min(top + self.item_height, self.image_height)
                box=[left,top,right,bottom]
                clip_image = self.max_image[box[1]:box[3],box[0]:box[2]]
                clip_image = self._pad_clip_image(clip_image)
                cii = ClipImageItem(self.coil_id,self.config.surface_key , box=box,image=clip_image)
                item_image_list.append(cii)
        return item_image_list

