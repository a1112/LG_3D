import pymssql
import numpy as np

from property.Base import CoilLineData, DataIntegration
from CONFIG import alarmConfigProperty
from CoilDataBase.models import AlarmTaperShape
from CoilDataBase import Alarm


def find_max_min_value(line,noneDataValue,offset=0):
    line_copy = np.copy(line)
    line_copy[line_copy<noneDataValue]=0
    mx,mn = np.argmax(line_copy), np.argmin(line_copy)
    mx,mn=int(mx),int(mn)
    return [mx+offset,float(line_copy[mx])],[mn+offset,float(line_copy[mn])]

def findTaperShapeValue(line,noneDataValue,offset=0):
    l_line_index=int(len(line)/2)
    max_minValue_l = find_max_min_value(line[:l_line_index],noneDataValue,offset)
    max_minValue_r = find_max_min_value(line[l_line_index:],noneDataValue,offset+l_line_index)
    return max_minValue_l,max_minValue_r

def findLRValue(line,offset=0):
    l_value=0
    r_value=len(line)-1
    for i in range(len(line)):
        if line[i]>0:
            l_value=i
            break
    for i in range(len(line)-1,-1,-1):
        if line[i]>0:
            r_value=i
            break
    return l_value+offset,r_value+offset

def split_line(detLine,maskLine,noneDataValue,ceter_x,ceter_y):
    c1 = CoilLineData()
    c2 = CoilLineData()


    l_line_p=findLRValue(maskLine[:ceter_x])
    r_line_p=findLRValue(maskLine[ceter_x:],ceter_x)
    l_mm_v = findTaperShapeValue(detLine[l_line_p[0]:l_line_p[1]],noneDataValue)
    r_mm_v= findTaperShapeValue(detLine[r_line_p[0]:r_line_p[1]],noneDataValue,r_line_p[0])

    c1.lineData=detLine
    c2.lineData=detLine
    c1.centre=[ceter_x,ceter_y]
    c1.centre=[ceter_x,ceter_y]
    c1.linePoint=[l_line_p[0],l_line_p[1]]
    c2.linePoint=[r_line_p[0],r_line_p[1]]
    c1.rotation_angle=180
    c2.rotation_angle=0

    return l_mm_v,r_mm_v, [c1,c2]

def addAlarmTaperShape(dataIntegration: DataIntegration,alarmTaperShape: AlarmTaperShape):
    alarmTaperShape.secondaryCoilId=dataIntegration.coilId
    alarmTaperShape.surface=dataIntegration.key
    Alarm.addAlarmTaperShape(alarmTaperShape)


def _detectionTaperShape_(dataIntegration: DataIntegration):
    print("塔形检测")
    x_cet_mm,y_cet_mm,accuracy_x=(dataIntegration.alarmFlat_Roll.inner_circle_center_x,
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


def _detectionTaperShapeAll_(dataIntegrationList):
    for dataIntegration in dataIntegrationList:
        if dataIntegration.hasDetectionError():
            continue
        _detectionTaperShape_(dataIntegration)