"""
封装3D数据拼接
"""


class LineData:
    """
    p1 到 p2 的 长度
    """

    def __init__(self, data):
        self.data = data
        self.length = len(data)