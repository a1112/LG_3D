from typing import List

from CoilDataBase.models import SecondaryCoil, AlarmFlatRoll, AlarmTaperShape, AlarmInfo
from CoilDataBase.Coil import addObj
from CONFIG import alarmConfigProperty, infoConfigProperty
from property.AlarmConfigProperty import AlarmFlatRollConfig, AlarmGradResult, TaperShapeConfig, LooseCoilConfig
from property.Base import CoilLineData, DataIntegration


def gradingAlarmFlatRoll(alarmFlat_Roll:AlarmFlatRoll,alarmFlatRollConfig:AlarmFlatRollConfig):
    """
    判断松卷的直接逻辑
    Args:
        alarmFlat_Roll:
        alarmFlatRollConfig:
    Returns:
    """
    name,configMax, configMin, configMsg=alarmFlatRollConfig.getConfig()
    errorMsg="正常"
    grad=1
    if alarmFlat_Roll.inner_circle_width<=configMin:
        errorMsg=f"{name} 内径 {alarmFlat_Roll.inner_circle_width} <= {configMin}"
        grad=3
    elif alarmFlat_Roll.inner_circle_width>=configMax:
        errorMsg=f"{name} 内径 {alarmFlat_Roll.inner_circle_width} >= {configMax}"
        grad=3
    return AlarmGradResult(grad, errorMsg,configMsg)

def gradingAlarmTaperShape(alarmTaperShapeList:List[AlarmTaperShape],taperShapeConfig:TaperShapeConfig):
    name,height_limit_list,inner,out,info = taperShapeConfig.getConfig()
    errorMsg="正常"
    grad=1
    for alarmTaperShape in alarmTaperShapeList:
        rotation_angle = alarmTaperShape.rotation_angle
        for height_limit_index,height_limit in enumerate(height_limit_list[::-1]):
            grading_level=3-height_limit_index
            if grad>=grading_level:
                continue
            if alarmTaperShape.out_taper_max_value>=height_limit:
                errorMsg+=f"外径最高值 {alarmTaperShape.out_taper_max_value} >= {height_limit} 检测角度{rotation_angle} \n"
                grad=grading_level
            if abs(alarmTaperShape.out_taper_min_value)>=height_limit:
                errorMsg+=f"外径最低值 abs({alarmTaperShape.out_taper_max_value}) >= {height_limit} 检测角度{rotation_angle} \n"
                grad=grading_level
            if alarmTaperShape.in_taper_max_value>=height_limit:
                errorMsg+=f"内径最高值 {alarmTaperShape.in_taper_max_value} >= {height_limit} 检测角度{rotation_angle} \n"
                grad=grading_level
            if alarmTaperShape.in_taper_min_value>=height_limit:
                errorMsg+=f"内径最低值 abs({alarmTaperShape.in_taper_min_value}) >= {height_limit} 检测角度{rotation_angle} \n"
                grad=grading_level
    return AlarmGradResult(grad, errorMsg,taperShapeConfig)

def gradingAlarmLooseCoil(detectionLineData:List[CoilLineData],looseCoilConfig:LooseCoilConfig):
    name,width,info = looseCoilConfig.getConfig()
    gradMsg=""
    grad=1

    for lineData in detectionLineData:
        if lineData.max_width_mm>width:
            gradMsg+=f"松卷检测最宽 {lineData.max_width_mm} 超过限制值 {width}"
            grad=3
    return AlarmGradResult(grad, gradMsg,looseCoilConfig)

def grading(dataIntegration:DataIntegration):

    """
        数据库提交判断级别
    Args:
        dataIntegration:

    Returns:

    """
    # 获取去向
    nextCode =str(chr(int(dataIntegration.currentSecondaryCoil.Weight)))
    nextName = infoConfigProperty.getNext(nextCode)
    flatRollGradInfo = gradingAlarmFlatRoll(dataIntegration.alarmFlat_Roll,alarmConfigProperty.getAlarmFlatRollConfig(nextCode))
    taperShapeGradInfo = gradingAlarmTaperShape(dataIntegration.alarmTaperShapeList,alarmConfigProperty.getTaperShapeConfig(nextCode))
    alarmLooseCoilInfo = gradingAlarmLooseCoil(dataIntegration.detectionLineData,alarmConfigProperty.getLooseCoilConfig(nextCode))

    alarmInfo = AlarmInfo(
        secondaryCoilId=dataIntegration.coilId,
        surface=dataIntegration.key,
        nextCode=nextCode,
        nextName = nextName,
        taperShapeGrad=taperShapeGradInfo.grad,
        taperShapeMsg=taperShapeGradInfo.errorMsg,
        looseCoilGrad=alarmLooseCoilInfo.grad,
        looseCoilMsg=alarmLooseCoilInfo.errorMsg,
        flatRollGrad=flatRollGradInfo.grad,
        flatRollMsg=flatRollGradInfo.errorMsg,
        defectGrad=1,
        defectMsg="",
        grad=max(taperShapeGradInfo.grad,alarmLooseCoilInfo.grad,flatRollGradInfo.grad)
    )
    print("add alarmInfo")
    addObj(alarmInfo)
