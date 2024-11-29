import pymssql
import numpy as np

from property.Base import DataIntegration, DataIntegrationList
from CoilDataBase.models import AlarmTaperShape
from CoilDataBase import Alarm

from TaperShapeLine import *


def addAlarmTaperShape(dataIntegration: DataIntegration,alarmTaperShape: AlarmTaperShape):
    alarmTaperShape.secondaryCoilId=dataIntegration.coilId
    alarmTaperShape.surface=dataIntegration.key
    Alarm.addAlarmTaperShape(alarmTaperShape)


def detectionTaperShapeByArea(dataIntegration: DataIntegration):
    pass

def _detectionTaperShape_(dataIntegration: DataIntegration):
    print("塔形检测")
    x_cet_mm,y_cet_mm,accuracy_x=(dataIntegration.flatRollData.inner_circle_center_x,
                       dataIntegration.alarmFlat_Roll.inner_circle_center_y,
                       dataIntegration.alarmFlat_Roll.accuracy_x)
    cx, cy=int(x_cet_mm/accuracy_x),int(y_cet_mm/accuracy_x)
    # maskNpy =
    maskLine = dataIntegration.npy_mask[cy,]
    detLine = dataIntegration.npyData[cy,]
    median_3d_mm = dataIntegration.median_3d_mm
    scan3dCoordinateScaleZ = dataIntegration.scan3dCoordinateScaleZ
    noneDataValue = -(median_3d_mm-100)
    detLine=detLine*scan3dCoordinateScaleZ-median_3d_mm
    l_mm_v, r_mm_v, coilLineDataList = split_line(detLine,maskLine,noneDataValue,cx,cy)


    def getAlarmTaperShape(mm_v,rotation_angle):

        out_v,in_rv=mm_v

        return AlarmTaperShape(
            out_taper_max_x=out_v[0][0],
            out_taper_max_y=out_v[0][1],
            out_taper_max_value=out_v[0][2],
            out_taper_min_x = out_v[1][0],
            out_taper_min_y=out_v[1][1],
            out_taper_min_value=out_v[1][2],
            in_taper_max_x = in_rv[0][0],
            in_taper_max_y = in_rv[0][1],
            in_taper_max_value = in_rv[0][2],
            in_taper_min_x = in_rv[1][0],
            in_taper_min_y = in_rv[1][1],
            in_taper_min_value = in_rv[1][2],
            rotation_angle=rotation_angle
        )

    def init_mm_v(mm_v):
        l_v,r_v=mm_v
        l_v_max,lv_min=l_v
        r_v_max,rv_min=r_v
        l_v_max=l_v_max[0],0,l_v_max[1]
        lv_min=lv_min[0],0,lv_min[1]
        rv_max=r_v_max[0],0,r_v_max[1]
        rv_min=rv_min[0],0,rv_min[1]
        return [[l_v_max,lv_min],[rv_max,rv_min]]

    ats1 = getAlarmTaperShape(init_mm_v(l_mm_v),180)
    ats2 = getAlarmTaperShape(init_mm_v(r_mm_v)[::-1], 0)

    dataIntegration.alarmTaperShapeList=[ats1,ats2]

    dataIntegration.detectionLineData = coilLineDataList


def _detectionTaperShapeAll_(dataIntegrationList:DataIntegrationList):
    """
    no doc
    """
    for dataIntegration in dataIntegrationList:
        _detectionTaperShape_(dataIntegration)