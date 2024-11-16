import numpy as np
import cv2


def render_list_as_jet_with_cv2(data, width=1000, height=100):
    # 将数据归一化到 0-255 的范围，适合 OpenCV 的颜色映射
    norm_data = np.array(data)
    norm_data = ((norm_data - norm_data.min()) / (norm_data.max() - norm_data.min()) * 255).astype(np.uint8)

    # 将一维数据转换为一个二维的条形高度图
    img = np.tile(norm_data, (height, 1))

    # 将 JET 颜色映射应用到数据
    jet_img = cv2.applyColorMap(img, cv2.COLORMAP_JET)

    # 调整图像大小（如需要）
    jet_img_resized = cv2.resize(jet_img, (width, height), interpolation=cv2.INTER_NEAREST)

    # 显示结果
    cv2.imshow('JET Rendered Image', jet_img_resized)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # 保存图像为文件
    cv2.imwrite('jet_rendered_image_cv2.png', jet_img_resized)


# 示例数据
data = np.random.rand(1000) * 10  # 假设有 1000 个随机数据点
render_list_as_jet_with_cv2(data)
