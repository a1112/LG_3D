import cv2
import numpy as np
import matplotlib.pyplot as plt

# 读取掩膜图像
mask1_path = 'mask1.bmp'  # 替换为你的掩膜图像路径
mask2_path = 'mask2.bmp'
mask3_path = 'mask3.bmp'

mask1 = cv2.imread(mask1_path, cv2.IMREAD_GRAYSCALE)
mask2 = cv2.imread(mask2_path, cv2.IMREAD_GRAYSCALE)
mask3 = cv2.imread(mask3_path, cv2.IMREAD_GRAYSCALE)

# 将掩膜图像二值化（确保只有0和255）
_, mask1 = cv2.threshold(mask1, 1, 255, cv2.THRESH_BINARY)
_, mask2 = cv2.threshold(mask2, 1, 255, cv2.THRESH_BINARY)
_, mask3 = cv2.threshold(mask3, 1, 255, cv2.THRESH_BINARY)


# 计算水平投影（每列的非零值）
def horizontal_projection_first_nonzero(mask):
    # 使用np.argmax找到第一个非零值的索引
    non_zero_indices = np.argmax(mask > 0, axis=0)
    # 处理整列都是零的情况
    non_zero_indices[np.all(mask == 0, axis=0)] = height
    return non_zero_indices


height, width = mask1.shape
mask2 = cv2.resize(mask2, (width, height))
mask3 = cv2.resize(mask3, (width, height))

proj1 = horizontal_projection_first_nonzero(mask1)
proj2 = horizontal_projection_first_nonzero(mask2)
proj3 = horizontal_projection_first_nonzero(mask3)


# 确定重叠区域
# overlap_mask = np.zeros_like(mask1)
# for col in range(mask1.shape[1]):
#     if proj1[col] > 0 and proj2[col] > 0 and proj3[col] > 0:
#         overlap_mask[:, col] = 255
print(proj1)
print(proj2)
print(proj3)
# 从每个掩膜中去除重叠区域
# mask1_no_overlap = cv2.bitwise_and(mask1, cv2.bitwise_not(overlap_mask))
# mask2_no_overlap = cv2.bitwise_and(mask2, cv2.bitwise_not(overlap_mask))
# mask3_no_overlap = cv2.bitwise_and(mask3, cv2.bitwise_not(overlap_mask))
#
# # 显示结果
# plt.figure(figsize=(15, 10))
#
# plt.subplot(3, 4, 1)
# plt.title('Mask 1')
# plt.imshow(mask1, cmap='gray')
#
# plt.subplot(3, 4, 2)
# plt.title('Mask 2')
# plt.imshow(mask2, cmap='gray')
#
# plt.subplot(3, 4, 3)
# plt.title('Mask 3')
# plt.imshow(mask3, cmap='gray')
#
# plt.subplot(3, 4, 4)
# plt.title('Overlap Mask')
# plt.imshow(overlap_mask, cmap='gray')
#
# plt.subplot(3, 4, 5)
# plt.title('Mask 1 (No Overlap)')
# plt.imshow(mask1_no_overlap, cmap='gray')
#
# plt.subplot(3, 4, 6)
# plt.title('Mask 2 (No Overlap)')
# plt.imshow(mask2_no_overlap, cmap='gray')
#
# plt.subplot(3, 4, 7)
# plt.title('Mask 3 (No Overlap)')
# plt.imshow(mask3_no_overlap, cmap='gray')
#
# plt.subplot(3, 4, 9)
# plt.title('Projection 1')
# plt.plot(proj1)
#
# plt.subplot(3, 4, 10)
# plt.title('Projection 2')
# plt.plot(proj2)
#
# plt.subplot(3, 4, 11)
# plt.title('Projection 3')
# plt.plot(proj3)
#
# plt.tight_layout()
# plt.show()