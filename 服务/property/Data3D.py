"""
封装3D数据拼接
"""
from tools.data3dTool import get_intersection_points
from skimage.draw import line

class LineData:
    """
    p1 到 p2 的 深度,数据
    """

    def __init__(self, npy_data,mask_image,p1, p2):
        self.npy_data = npy_data
        self.mask_image = mask_image
        self.p1 = p1
        self.p2 = p2

    def get_line_border(self):
        h, w = self.mask_image.shape
        return get_intersection_points(self.p1, self.p2, w, h)

    def point_hasData(self,point):
        return point>100

    def get_line_points(self,mask=True):
        """
        获取线段的所有点
        """
        pL, pR = self.get_line_border()
        rr, cc = line(pL[0], pL[1], pR[0], pR[1])
        if not mask:
            return rr, cc
        intersection_rr = []
        intersection_cc = []
        self.mask_image[cc[0], rr[0]] = 0
        self.mask_image[cc[-1], rr[-1]] = 0
        hasSteel = False
        for r, z in zip(rr, cc):
            if self.point_hasData(self.mask_image[z, r]):
                intersection_rr.append(r)
                intersection_cc.append(z)
                hasSteel = True
            elif self.point_hasData(self.mask_image[z, r]) and hasSteel:
                intersection_rr.append(r)
                intersection_cc.append(z)
                hasSteel = False
        # 初始化存储线段的列表
        lines = []
        # 提取每一对交点之间的线段值

        for i in range(0, len(intersection_rr) - 1, 2):
            # 获取当前和下一个交点
            pl = (intersection_rr[i], intersection_cc[i])
            pr = (intersection_rr[i + 1], intersection_cc[i + 1])
            # 使用 Bresenham's line algorithm 获取 pl 和 pr 之间的所有点
            segment_rr, segment_cc = line(pl[0], pl[1], pr[0], pr[1])
            # 从 npy 数据中提取这些点对应的值
            segment_values = self.npy_data[segment_cc, segment_rr]
            # 将这些点的坐标和对应的值组合在一起
            segment_points = list(
                zip(list(segment_rr.tolist()), list(segment_cc.tolist()), list(segment_values.tolist())))
            if len(segment_points) > 100:
                lines.append({
                    "len": len(segment_points),
                    "points": segment_points,
                    "pointL": [int(pl[0]), int(pl[1])],
                    "pointR": [int(pr[0]), int(pr[1])],
                    # "min":int(np.min(segment_values)),
                    # "max":int(np.max(segment_values)),
                    # "mean":int(np.mean(segment_values)),
                    # "std":int(np.std(segment_values)),
                    # "median":int(np.median(segment_values)),
                })

        return lines