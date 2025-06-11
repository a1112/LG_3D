import cv2
import numpy as np
from ultralytics.engine.results import Results
from PIL import Image

class YoloModelResultsBase:
    def __init__(self, image, result):
        self.result:Results = result
        if isinstance(image, str):
            self.image = cv2.imread(image)
        if isinstance(image, Image.Image):
            self.image = np.array(image)
        else:
            self.image = image
        self.image: np.ndarray


    @property
    def all_names(self):
        return self.result.names

    @property
    def boxes(self):
        return self.result.boxes

class YoloModelDetResults(YoloModelResultsBase):
    def __init__(self, image, result):
        super(YoloModelDetResults, self).__init__(image, result)

class YoloModelSegResults(YoloModelResultsBase):
    def __init__(self, image, result):
        super(YoloModelSegResults, self).__init__(image, result)

    @property
    def contour(self):
        cons = []
        for i, (box, mask) in enumerate(zip(self.result.boxes, self.result.masks)):
            contours = mask.xy
            # 绘制轮廓（在原图上）
            contour = np.array(contours, dtype=np.float32)  # 保持浮点精度
            contour_int = np.round(contour).astype(np.int32)
            cons.append(contour_int)
        return cons

    def get_draw(self,image=None):
        if image is None:
            image = self.image.copy()

        cv2.drawContours(
            image,
            self.contour.copy(),
            -1,  # 绘制所有轮廓
            (0, 255, 0),  # 绿色
            -1  # 线宽
        )
        return image

    def show(self):
        """
         opencv 显示轮廓
        """
        draw_image = self.get_draw()
        resized_image = cv2.resize(draw_image, (512, 512))  # 例如，将图像大小调整为640x480像素

        Image.fromarray(resized_image).show()
        # # 显示结果
        # cv2.imshow(f"Object Contours", resized_image)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

    def to_labelme_json(self):
        """
        Convert the segmentation results to a labelme format.
        """
        self.image: np.ndarray
        labelme_data = {
            "version": "4.5.6",
            "flags": {},
            "shapes": [],
            "imagePath": "",
            "imageData": None,
            "imageHeight": self.image.shape[0],
            "imageWidth": self.image.shape[1]
        }

        for i, (box, mask) in enumerate(zip(self.result.boxes, self.result.masks)):
            contours = mask.xy
            contour = np.array(contours, dtype=np.float32)
            contour_int = np.round(contour).astype(np.int32).tolist()
            labelme_data["shapes"].append({
                "label": self.all_names[box.cls],
                "points": contour_int,
                "group_id": None,
                "shape_type": "polygon",
                "flags": {}
            })

        return labelme_data