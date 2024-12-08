from typing import Optional

from CoilDataBase.Alarm import addAlarmFlatRoll
from CoilDataBase.models import AlarmFlatRoll

from .Base import BaseData
from .. import Point2D


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


class FlatRollData(BaseData):
    """
        中间检测数据
    """

    def __init__(self, dataIntegration, inner_circle=None, out_circle=None):
        super().__init__(dataIntegration)
        self.inner_circle: Optional[CircleDataItem] = inner_circle
        self.out_circle: Optional[CircleDataItem] = out_circle

    def set_out_circle(self, circle: CircleDataItem):
        self.out_circle = circle

    def set_inner_circle(self, circle: CircleDataItem):
        self.inner_circle = circle

    def get_center(self):
        return Point2D(self.inner_circle.ellipse.center_x,
                       self.inner_circle.ellipse.center_y)

    def getAlarmFlatRoll(self, dataIntegration=None):
        if dataIntegration is None:
            dataIntegration = self.dataIntegration
        return AlarmFlatRoll(
            secondaryCoilId=dataIntegration.coilId,
            surface=dataIntegration.key,
            out_circle_width=self.out_circle.ellipse.width,
            out_circle_height=self.out_circle.ellipse.height,
            out_circle_center_x=self.out_circle.ellipse.center_x,
            out_circle_center_y=self.out_circle.ellipse.center_y,
            out_circle_radius=self.out_circle.circle.radius,
            inner_circle_width=self.inner_circle.ellipse.width,
            inner_circle_height=self.inner_circle.ellipse.height,
            inner_circle_center_x=self.inner_circle.ellipse.center_x,
            inner_circle_center_y=self.inner_circle.ellipse.center_y,
            inner_circle_radius=self.inner_circle.circle.radius,
            accuracy_x=dataIntegration.accuracy_x,
            accuracy_y=dataIntegration.accuracy_y,
        )

    def commit(self):
        """
        救数据结构
        """
        return addAlarmFlatRoll(self.getAlarmFlatRoll())
