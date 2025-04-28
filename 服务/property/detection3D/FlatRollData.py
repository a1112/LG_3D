class CircleDataCircle:
    def __init__(self, data):
        self.data = data
        self.center_x = data[0]
        self.center_y = data[1]
        self.radius = data[2]

    def __repr__(self):
        return f"CircleDataCircle({self.center_x},{self.center_y},{self.radius})"


class CircleDataEllipse:
    def __init__(self, data):
        self.data = data
        self.center_x = data[0][0]
        self.center_y = data[0][1]
        self.width = data[1][0]
        self.height = data[1][1]
        self.rotation_angle = data[2]

    def __repr__(self):
        return f"CircleDataEllipse({self.center_x},{self.center_y},{self.width},{self.height},{self.rotation_angle})"


class CircleDataItem:
    def __init__(self, data, key):
        self.data = data
        self.key = key
        self.circle = CircleDataCircle(data["circle"])
        self.ellipse = CircleDataEllipse(data["ellipse"])
        # 内接圆
        self.inner_circle = CircleDataCircle(data["inner_circle"])


