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

        if self.result.masks is None:
            return cons

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
            5  # 线宽
        )
        return image
    def get_mask(self):
        """
        获取掩码
        """
        if self.result.masks is None:
            return None
        mask = self.result.masks.data.cpu().numpy()
        mask = np.sum(mask, axis=0)
        mask = np.squeeze(mask)
        mask = (mask * 255).astype(np.uint8)
        # 只保留最大轮廓
        gray = mask
        # 3. 图像二值化
        # 使用 THRESH_BINARY_INV 还是 THRESH_BINARY 取决于你的前景物体是亮还是暗
        # _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)

        # 4. 查找轮廓
        # 使用 RETR_EXTERNAL 只检测最外层轮廓，CHAIN_APPROX_SIMPLE 压缩轮廓点
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 5. 找到最大轮廓
        # 如果图像中确实检测到了轮廓
        if contours:
            # 计算所有轮廓面积并找到最大轮廓的索引
            areas = [cv2.contourArea(cnt) for cnt in contours]
            max_idx = np.argmax(areas)
            max_contour = contours[max_idx]

            # 6. 创建一个空白掩码（全黑）
            mask = np.zeros_like(gray)
            # 6.1 在掩码上绘制并填充最大轮廓（白色）
            # 使用 cv2.drawContours 并设置 thickness=cv2.FILLED 进行填充
            cv2.drawContours(mask, [max_contour], -1, 255, cv2.FILLED)

            # 7. （可选）应用掩码到原图，只保留最大轮廓区域
            # 按位与操作，掩码中白色区域保留原图，黑色区域置为0（黑）
            # result = cv2.bitwise_and(gray, gray, mask=mask)
        mask = cv2.resize(mask, (512,512))
        return mask


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

