from collections.abc import Mapping
from typing import Union

from Base.property.Base import DataIntegration, DataIntegrationList
from Base.utils.Log import logger
import numpy as np


# Function to group consecutive rows
def group_consecutive(arr):
    groups = []
    current_group = [arr[0]] if arr.size > 0 else []

    for i in range(1, len(arr)):
        if arr[i, 0] == arr[i - 1, 0] + 1:  # Check if consecutive
            current_group.append(arr[i])
        else:
            groups.append(np.array(current_group))
            current_group = [arr[i]]

    if current_group:
        groups.append(np.array(current_group))  # Append the last group

    return groups


class AlarmLooseData:

    def __init__(self, lineDatas):
        self.dataIntegrationList = [d[0] for d in lineDatas]
        self.lineDatas = [d[1] for d in lineDatas]
        self.lineDataDicts = {}
        common_rotations = set(self.lineDatas[0]).intersection(
            self.lineDatas[1])
        missing_by_surface = [
            sorted(set(line_data) - common_rotations)
            for line_data in self.lineDatas
        ]
        if any(missing_by_surface):
            logger.warning(
                "loose coil rotation mismatch: coil=%s surfaces=%s "
                "common=%s unmatched=%s",
                self.dataIntegrationList[0].coilId,
                [data.surface for data in self.dataIntegrationList],
                sorted(common_rotations),
                missing_by_surface,
            )
        for rotate in sorted(common_rotations):
            self.lineDataDicts[rotate] = [
                self.lineDatas[0][rotate], self.lineDatas[1][rotate]
            ]

    def detection(self):
        return {
            rotate: tuple(line.max_zero_width_mm for line in lines)
            for rotate, lines in self.lineDataDicts.items()
        }


def _detectionAlarmLooseCoil_(data_integration: DataIntegration):
    """Measure each available ray; one failed ray must not hide valid gaps."""
    alarm_data = data_integration.alarmData
    alarm_data.loose_coil_measurements = []
    alarm_data.loose_coil_errors = []
    line_data = getattr(alarm_data, "lineDataDict", None) or {}
    if isinstance(line_data, Mapping):
        items = line_data.items()
    elif isinstance(line_data, (list, tuple)):
        items = enumerate(line_data)
    else:
        alarm_data.loose_coil_errors.append("无效径向线数据")
        return []
    for key, line in items:
        try:
            angle = float(getattr(line, "rotation_angle", None)
                          if getattr(line, "rotation_angle", None) is not None else key)
            width = float(line.max_zero_width_mm)
            if not np.isfinite(angle) or not np.isfinite(width) or width < 0:
                raise ValueError("非有限角度或间隙宽度")
            segments = [list(segment) for segment in line.none_data_sub]
            alarm_data.loose_coil_measurements.append({
                "rotation_angle": angle % 360,
                "max_width_mm": width,
                "segments": segments,
            })
        except (AttributeError, ValueError, TypeError, IndexError, OverflowError) as e:
            alarm_data.loose_coil_errors.append(f"{key}度: {e}")
    return alarm_data.loose_coil_measurements


def _detectionAlarmLooseCoilAll_(
        data_integration_list: Union[DataIntegrationList, DataIntegration]):
    """
    获取 LineData 数据假设同角度检测
    """
    if isinstance(data_integration_list, DataIntegration):
        data_integration_list = [data_integration_list]
    for dataIntegration in data_integration_list:
        _detectionAlarmLooseCoil_(dataIntegration)
