import numpy as np


def IQR_outliers(data):
    Q1 = np.percentile(data, 10)
    Q3 = np.percentile(data, 90)

    # 计算 IQR（四分位距）
    IQR = Q3 - Q1

    # 定义异常值的下限和上限
    # lower_bound = Q1 - 1.5 * IQR
    # upper_bound = Q3 + 1.5 * IQR
    lower_bound = Q1 - 3 * IQR
    upper_bound = Q3 + 3 * IQR
    # 找到异常值
    IQR_outliers = data[(data < lower_bound) | (data > upper_bound)]
    return IQR_outliers