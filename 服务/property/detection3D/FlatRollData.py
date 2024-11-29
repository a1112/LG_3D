from typing import Optional

from CoilDataBase.Alarm import addObj
from CoilDataBase.models import AlarmFlatRoll

from .Base import BaseData
from .. import Point2D


class CircleDataCircle:
    def __init__(self, data):
        self.data = data
        self.center_x=data[0]
        self.center_y=data[1]
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
    def __init__(self, data,key):
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
    def __init__(self,dataIntegration,inner_circle=None,out_circle=None):
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

    def getAlarmFlatRoll(self):
        return AlarmFlatRoll(
            secondaryCoilId=self.dataIntegration.coilId,
            surface=self.dataIntegration.key,
            out_circle_width=self.out_circle.circle[2],
            out_circle_height=self.out_circle.circle[2],
            out_circle_center_x=self.out_circle.circle[0],
            out_circle_center_y=self.out_circle.circle[1],
            out_circle_radius=self.out_circle.circle[2],
            inner_circle_width=self.inner_circle.circle[2],
            inner_circle_height=self.inner_circle.circle[2],
            inner_circle_center_x=self.inner_circle.circle[0],
            inner_circle_center_y=self.inner_circle.circle[1],
            inner_circle_radius=self.inner_circle.circle[2],
            accuracy_x=self.dataIntegration.accuracy_x,
            accuracy_y=self.dataIntegration.accuracy_y,
            accuracy_z=self.dataIntegration.accuracy_z,
        )
    def __del__(self):

        pass


    #     return AlarmFlatRoll(
    #     secondaryCoilId=dataIntegration.coilId,
    #     surface=dataIntegration.key,
    #     out_circle_width=circle_data_out.ellipse[1][0] * accuracy_x,
    #     out_circle_height=circle_data_out.ellipse[1][1] * accuracy_x,
    #     out_circle_center_x=circle_data_out.ellipse[0][0] * accuracy_x,
    #     out_circle_center_y=circle_data_out.ellipse[0][1] * accuracy_x,
    #     out_circle_radius=circle_data_out.ellipse[2] * accuracy_x,
    #     inner_circle_width=circle_data_in.ellipse[1][0] * accuracy_x,
    #     inner_circle_height=circle_data_in.ellipse[1][1] * accuracy_x,
    #     inner_circle_center_x=circle_data_in.ellipse[0][0] * accuracy_x,
    #     inner_circle_center_y=circle_data_in.ellipse[0][1] * accuracy_x,
    #     inner_circle_radius=circle_data_in.ellipse[2] * accuracy_x,
    #     accuracy_x=accuracy_x,
    #     accuracy_y=accuracy_y,
    #     level=level,
    #     err_msg=errorStr
    # )