import cv2

from JoinService.cv_count_tool import im_show
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
        self.clip_number = 10
        self.item_width = None
        self.item_height = None


    def set_max_image(self, max_image):
        if isinstance(max_image, str):
            max_image = cv2.imread(max_image)
        self.max_image = max_image
        self.image_width = max_image.shape[1]
        self.image_height = max_image.shape[0]
        self.item_width = max_image.shape[1]//self.clip_number
        self.item_height = max_image.shape[0]//self.clip_number

    def clip_image(self):
        """
        将图像拆封为 n*n 块
        """
        item_image_list=[]
        for row_id in range(self.clip_number):
            for col_id in range(self.clip_number):
                box=[self.item_width*row_id,self.item_height*col_id,self.item_width*row_id+self.item_width,self.item_height*col_id+self.item_height]
                clip_image = self.max_image[box[1]:box[3],box[0]:box[2]]
                cii = ClipImageItem(self.coil_id,self.config.surface_key , box=box,image=clip_image)
                item_image_list.append(cii)
        return item_image_list

