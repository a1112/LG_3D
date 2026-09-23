import json
from typing import Optional

import numpy as np

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
        grade = getattr(getattr(data_integration, "alarmData", None), "flat_roll_grad_result", None)
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
            level=getattr(grade, "grad", None),
            err_msg=getattr(grade, "errorMsg", None),
            data=json.dumps({
                "inner_diameter_mm": self.inner_diameter_mm(),
                "inner_ellipse_angle": float(self.inner_circle.ellipse.rotation_angle),
                "outer_ellipse_angle": float(self.out_circle.ellipse.rotation_angle),
            }, allow_nan=False),
        )

    @property
    def inner_circle_width(self):
        return self.inner_circle.ellipse.width

    def inner_diameter_mm(self) -> float:
        """Return the ellipse's minor diameter after X/Y calibration."""
        ellipse = self.inner_circle.ellipse
        scale_x = float(self.dataIntegration.scan3dCoordinateScaleX)
        scale_y = float(self.dataIntegration.scan3dCoordinateScaleY)
        width, height = float(ellipse.width), float(ellipse.height)
        angle = float(ellipse.rotation_angle)
        values = (scale_x, scale_y, width, height, angle)
        if not all(np.isfinite(value) for value in values):
            raise ValueError("扁卷椭圆或标定包含非有限值")
        if min(scale_x, scale_y, width, height) <= 0:
            raise ValueError("扁卷椭圆轴长与标定比例必须大于零")
        radians = np.deg2rad(angle)
        rotation = np.array([[np.cos(radians), -np.sin(radians)],
                             [np.sin(radians), np.cos(radians)]])
        calibrated = np.diag([scale_x, scale_y]) @ rotation @ np.diag([width, height])
        return float(np.linalg.svd(calibrated, compute_uv=False).min())

    def commit(self):
        """
        救数据结构
        """
        return addAlarmFlatRoll(self.get_alarm_flat_roll())
