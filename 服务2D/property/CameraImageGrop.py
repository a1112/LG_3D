from typing import List

from JoinService.cv_count_tool import get_intersections, hconcat_list, im_show
from area_alg.YoloModelResults import YoloModelSegResults
from configs import CONFIG
from configs.CONFIG import DEBUG
from configs.DebugConfigs import debug_config


class CameraImageGrop:
    def __init__(self,coil_id,config, results:List[YoloModelSegResults]):
        self.results = results
        self.config = config
        self.coil_id = coil_id
        if CONFIG.DEBUG:
            for i, seg_result in enumerate(results):
                draw_image = seg_result.get_draw()
                debug_config.save_simple_image(draw_image, f"seg_{self.config.key}_{i}.jpg")

                mask_image = seg_result.get_mask()
                if mask_image is not None:
                    try:
                        debug_config.save_mask_image(mask_image, f"mask_{self.config.key}_{i}.jpg")
                    except Exception as e:
                        print(f"Error saving mask image: {e}")


        self.mask_list=[]
        self.image_list=[]
        for seg_result in results:
            seg_result: "YoloModelSegResults"
            mask = seg_result.get_mask()
            if mask is not None:
                self.mask_list.append(mask)
                self.image_list.append(seg_result.image)
        self.intersections = get_intersections(self.mask_list)
        self.intersections = [i * 10 for i in self.intersections]

        for mask, image in zip(self.mask_list, self.image_list):
            im_show(mask, fr"mask {self.config.key}")
            im_show(image, fr"image {self.config.key}")

    def join_image(self):

        print(fr"intersections {self.coil_id} {self.config.key} {self.intersections}")
        image = hconcat_list(self.image_list, self.intersections)

        if DEBUG:

            im_show(image,fr"join_image {self.config.key}")

        return image