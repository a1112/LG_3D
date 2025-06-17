from pathlib import Path

from PIL import Image

from area_alg.YoloModelResults import YoloModelSegResults
from area_alg.YoloSeg import SteelSegModel
from configs.CONFIG import DEBUG
from configs.DebugConfigs import debug_config
from utils.MultiprocessColorLogger import logger

from property.CameraImageGrop import CameraImageGrop
from utils.DetectionSpeedRecord import DetectionSpeedRecord
from .cv_count_tool import get_intersections, hconcat_list
from .SaverWork import DebugSaveWork
from .WorkBase import WorkBaseThread
from configs.CameraConfig import CameraConfig
from configs import CONFIG

model = SteelSegModel()

class CameraWork(WorkBaseThread):
    """
    相机加载线程
    """
    def __init__(self, config):
        super().__init__(config)
        self.scale = 1
        self.start()
        self.config:CameraConfig
        self.surface_key=config.surface_key
        self.key = config.key
        self.debug_work = None

        if CONFIG.DEBUG:
            self.debug_work = DebugSaveWork(self.config)

    @DetectionSpeedRecord.timing_decorator("图像: 获取")
    def get_images(self, folder,coil_id):
        image_url_list = list(folder.glob("*.jpg"))
        image_url_list.sort(key=lambda i: int(Path(i).stem))
        image_url_list = self.config.get_url_list(image_url_list)
        image_list = [Image.open(u).convert("RGB") for u in image_url_list]

        if self.debug_work is not None:
            for url_,image_ in zip(image_url_list,image_list):
                index = Path(url_).stem
                self.debug_work.add_work([coil_id, self.config.key, index, image_.copy()])


        return image_list

    def run(self):
        self.config: CameraConfig
        while self._run_:
            coil_id = self.queue_in.get()
            if not self.config.is_run():
                return
            folder = self.config.get_folder(coil_id)
            images = self.get_images(folder, coil_id)
            try:
                camera_image_grop = self.horizontal_concat(images)

                # print(max_image)
                # max_image.save(fr"test_{self.config.key}.jpg")
                self.set(camera_image_grop)
            except BaseException as e:
                print(e)
                print(images)
                self.set(None)
                if DEBUG:
                    raise e

    @DetectionSpeedRecord.timing_decorator("图像拼接 ")
    def horizontal_concat(self,images):
        """
        单行数据的拼接流程
        Args:
            images:

        Returns:

        """

        seg_results = model.predict(images)
        return CameraImageGrop(self.config, seg_results)

        # seg_result_list = []
        # for i, image in enumerate(images):
        #     seg_results = model.predict_one(image)
        #
        #     if CONFIG.DEBUG:
        #         draw_image = seg_results.get_draw()
        #         debug_config.save_simple_image(draw_image, f"seg_{self.config.key}_{i}.jpg")
        #
        #         mask_image = seg_results.get_mask()
        #         if mask_image is not None:
        #             try:
        #                 debug_config.save_mask_image(mask_image, f"mask_{self.config.key}_{i}.jpg")
        #             except Exception as e:
        #                 print(f"Error saving mask image: {e}")
        #
        #     seg_result_list.append(seg_results)
        #
        # return self.join_image(seg_result_list)



    def join_image(self,seg_result_list):
        mask_list=[]
        image_list=[]
        for seg_result in seg_result_list:
            seg_result: "YoloModelSegResults"
            mask = seg_result.get_mask()
            if mask is not None:
                mask_list.append(mask)
                image_list.append(seg_result.image)
        intersections = get_intersections(mask_list)
        intersections =[ i*10 for i in intersections]

        print(fr"intersections {intersections}")
        return hconcat_list(image_list,intersections)