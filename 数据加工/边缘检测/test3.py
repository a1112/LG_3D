import cv2
import numpy as np
import matplotlib.pyplot as plt


def find_nearest_circle(image, target_point):
    """
    在图像中查找最接近的圆形对象。
    """
    # 转换为灰度图像
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 使用霍夫圆变换检测圆形
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=30,
        param1=50,
        param2=30,
        minRadius=5,
        maxRadius=100
    )

    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")

        # 查找与目标点距离最近的圆形
        min_distance = float("inf")
        nearest_circle = None

        for (x, y, r) in circles:
            distance = np.sqrt((x - target_point[0]) ** 2 + (y - target_point[1]) ** 2)
            if distance < min_distance:
                min_distance = distance
                nearest_circle = (x, y, r)

        return nearest_circle
    else:
        return None


# 示例图像路径
image_path = 'join_1747.jpg'  # 替换为你的图像路径
image = cv2.imread(image_path)

# 目标点
target_point = (100, 100)  # 替换为你要查找的目标点

# 查找最接近的圆形
nearest_circle = find_nearest_circle(image, target_point)

if nearest_circle is not None:
    x, y, r = nearest_circle
    print(f"Nearest circle: center=({x}, {y}), radius={r}")

    # 绘制结果
    output = image.copy()
    cv2.circle(output, (x, y), r, (0, 255, 0), 2)
    cv2.circle(output, target_point, 5, (255, 0, 0), -1)  # 绘制目标点

    plt.imshow(cv2.cvtColor(output, cv2.COLOR_BGR2RGB))
    plt.title('Nearest Circle Detection')
    plt.show()
else:
    print("No circles found.")
