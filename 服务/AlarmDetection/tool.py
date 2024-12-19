import math


def calculate_angle(ax, ay, bx, by):
    # 计算 AB 向量的角度
    delta_x = bx - ax
    delta_y = by - ay

    # atan2 返回弧度，使用 degrees 将其转换为角度
    angle_radians = math.atan2(delta_y, delta_x)
    angle_degrees = math.degrees(angle_radians)

    return angle_degrees

