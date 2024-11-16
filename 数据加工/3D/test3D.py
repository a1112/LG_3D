import numpy as np
from matplotlib import pyplot as plt

data3D = np.load(fr"F:\datasets\LG_3D_DataBase\DataSave\surface_S\1759\3D.npy")
print(data3D.shape)
non_zero_elements_0 = data3D[data3D > 100]

# 计算非零元素的中位数
median_non_zero = np.median(non_zero_elements_0)
print(median_non_zero)
data3D[data3D <  median_non_zero-2000] = 0
data3D[data3D > median_non_zero+2000] = 0
print(data3D.sum())
non_zero_elements = data3D[data3D != 0]

# non_zero_elements = data3D[data3D < median_non_zero+1000]
# 将二维数组转换为一维数组
flat_arr = non_zero_elements.flatten()
# 筛选出非零元素
print(non_zero_elements.shape)
# 绘制直方图


plt.hist(non_zero_elements, bins='auto', alpha=0.7, rwidth=0.85)
plt.title('Distribution of Non-Zero Elements')
plt.xlabel('Value')
plt.ylabel('Frequency')
plt.grid(axis='y', alpha=0.75)
plt.show()