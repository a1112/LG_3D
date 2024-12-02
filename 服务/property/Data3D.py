"""
封装3D数据拼接
"""
import numpy as np
from skimage.draw import line

from tools.tool import get_intersection_points


class LineData:
    """
    p1 到 p2 的 深度,数据
    """

    def __init__(self, npy_data,mask_image,p1, p2):
        self.npy_data = npy_data
        self.mask_image = mask_image
        self.p1 = p1
        self.p2 = p2
        self.image_threshold = 100

    def get_edge_point(self):
        """
        获取与图像边缘相交的两个点
        """
        h, w = self.mask_image.shape
        return get_intersection_points(self.p1, self.p2, w, h)

    def point_hasData(self,point):
        return point>self.image_threshold

    def all_image_line_points(self, mask=False, ray=False):
        """
        获取 直线经过图像 的所有点 x，y ,z
        """
        p1, p2 = self.get_edge_point()
        rr, cc = line(p1.x, p1.y, p2.x, p2.y)
        if ray: # 射线模式,只对线段进行判断
            def directionEqual(direction1, direction2): # 计算两个方向是否相等
                return direction1[0] == direction2[0] and direction1[1] == direction2[1]
            direction = (self.p2[0] - self.p1[0]>0, self.p2[1] - self.p1[1]>0 )
            rr,cc = list(zip(*[[r,c] for r,c in zip(rr, cc) if directionEqual(direction,(r-self.p1.x>0,c-self.p1.y>0))]))
        if not mask:
            zz = self.npy_data[cc, rr]
            return np.array(list(zip(rr, cc, zz)))
        else:
            zz_mask = self.mask_image[cc, rr]
            zz= np.where(zz_mask > self.image_threshold, self.npy_data[cc, rr], 0)
            return np.array(list(zip(rr, cc, zz)))

    def mask_image_line_points(self):
        """
        过滤mask外的点
        Returns:

        """
        return self.all_image_line_points(mask=True)

    def split_image_line_points(self):
        """
        过滤mask外的点,然后进行分段
        Returns:
        """
        oldHasSteel = False # 记录上一个点的状态
        lines=[]
        lineItem=[]
        for point in self.mask_image_line_points():
            """
            扫描一次实现全部的分段
            """
            hasSteel=self.point_hasData(point[2])
            if hasSteel and not oldHasSteel:
                # 新的线段
                lineItem.append(point)

            elif hasSteel and oldHasSteel:
                lineItem.append(point)
            elif not hasSteel and oldHasSteel:
                if len(lineItem)>100:
                    lines.append(lineItem)
                    lineItem=[]
            oldHasSteel = hasSteel
        if lineItem:
            lines.append(lineItem)
        return lines

    def get_line_points(self,mask=True,ray=False):
        """
        获取线段的所有点
        """
        p1, p2 = self.get_edge_point()
        rr, cc = line(p1.x, p1.y, p2.x, p2.y)
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

        for i in range(0, len(intersection_rr) - 1):
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

    def get_line_json(self):
        pass

    def detTaperShape(self):
        """
        返回到 内外塔形的最大最小值
        Returns:
        """
        points = self.all_image_line_points(mask=True, ray=True)
        arr = np.array(list(points))
        non_zero_indices = np.where(arr[:, 2] != 0)[0]
        # 起始索引和结束索引
        start_index = non_zero_indices[0]
        end_index = non_zero_indices[-1]
        print(arr[start_index],"  ",arr[end_index])
        input()