import numpy as np
import matplotlib.pyplot as plt
from sklearn import svm

normal_samples = np.random.randn(100, 2)

# 生成异常样本
outliers = np.random.uniform(low=-40, high=4, size=(5, 2))
print(outliers)
# 合并正常样本和异常样本
X = np.vstack((normal_samples, outliers))

# 训练One-Class SVM模型
clf = svm.OneClassSVM(nu=0.05, kernel="rbf", gamma=0.1)
clf.fit(X)

# 预测样本是否为异常
y_pred = clf.predict(X)

# 可视化结果
plt.scatter(X[:, 0], X[:, 1], c=y_pred, cmap='viridis')
plt.title('One-Class SVM for Outlier Detection')
plt.show()

