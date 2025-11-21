from typing import Optional

from CoilDataBase.Alarm import addAlarmFlatRoll
from CoilDataBase.models import AlarmFlatRoll

from .BaseData import BaseData
from Base.property.Types import Point2D
from Base.property.detection3D import CircleDataItem


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

    def get_alarm_flat_roll(self, data_integration=None):
        if data_integration is None:
            data_integration = self.dataIntegration
        return AlarmFlatRoll(
            secondaryCoilId=data_integration.coilId,
            surface=data_integration.key,
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
            accuracy_x=data_integration.accuracy_x,
            accuracy_y=data_integration.accuracy_y,
        )

    @property
    def inner_circle_width(self):
        return self.inner_circle.ellipse.width

    def commit(self):
        """
        救数据结构
        """
        return addAlarmFlatRoll(self.get_alarm_flat_roll())
