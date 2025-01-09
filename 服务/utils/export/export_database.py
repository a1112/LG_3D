from collections import OrderedDict, defaultdict

from CoilDataBase import Coil
from CoilDataBase.models import AlarmFlatRoll, CoilDefect
from CoilDataBase.models import PlcData
from CoilDataBase.models import CoilState
from CoilDataBase.models import SecondaryCoil
from CoilDataBase.models import AlarmTaperShape
from CoilDataBase.models import AlarmLooseCoil
from CoilDataBase.models import AlarmInfo
import Globs
from .export_tool import format_time ,spit_data_list

from .export_config import ExportConfig


def get_header_data(secondary_coil:SecondaryCoil):
    coil_list = secondary_coil.childrenCoil
    if coil_list:
        coil=coil_list[0]
        coil:Coil
        # res_data.update({
        #     "检测完成日期":formatTime(coil.DetectionTime),
        # })
    return  OrderedDict({
                "流水号": secondary_coil.Id,
                "卷号": secondary_coil.CoilNo,
                "钢种": secondary_coil.CoilType,
                "去向": Globs.infoConfigProperty.getNext(secondary_coil.Weight),
                # "二级内径": secondary_coil.CoilInside,
                "二级外径": secondary_coil.CoilDia,
                "二级厚度": secondary_coil.Thickness,
                "二级宽度": secondary_coil.Width,
                # "二级目标宽度": secondary_coil.ActWidth,
                "二级数据接受时间": format_time(secondary_coil.CreateTime),
            })

def get_plc_data(secondary_coil:SecondaryCoil):
    plc_data_list = secondary_coil.childrenPlcData

    if len(plc_data_list):
        plc_data=plc_data_list[0]
        plc_data:PlcData
        return {
            "激光距离":plc_data.location_laser,
            "S端移动位置":plc_data.location_L,
            "L端移动位置":plc_data.location_S,
        }



def get_coil_state(secondary_coil):
    res_data={}
    coil_state_list=secondary_coil.childrenCoilState
    if len(coil_state_list):
        coil_state=coil_state_list[0]
        coil_state:CoilState
        res_data.update({
            "X 标定":coil_state.scan3dCoordinateScaleX,
            "Y 标定":coil_state.scan3dCoordinateScaleY,
            "Z 标定":coil_state.scan3dCoordinateScaleZ,
        })
    return res_data

def get_alarm_info(secondary_coil,alarm_info_dict):
    res_data={}
    alarm_flat_roll_list = secondary_coil.childrenAlarmFlatRoll
    alarm_flat_roll_dict={"S":[],"L":[]}
    [alarm_flat_roll_dict[alarmFlatRoll.surface].append(alarmFlatRoll) for alarmFlatRoll in alarm_flat_roll_list]
    for key, value in alarm_flat_roll_dict.items():
        if len(value):
            alarm_flat_roll=value[0]
            alarm_flat_roll:AlarmFlatRoll
            res_data.update({
                key + "端 检测外径":alarm_flat_roll.out_circle_width,
                key + "端 检测内径":alarm_flat_roll.inner_circle_width,
                # 更多参数
            })
            if alarm_info_dict[key]:
                alarm_info=alarm_info_dict[key]
                alarm_info:AlarmInfo
                res_data.update({
                    key + "端 扁卷报警等级":alarm_info.flatRollGrad,
                    key + "端 扁卷报警信息": alarm_info.flatRollMsg,
                })
    return res_data

def get_taper_shape_info(secondary_coil,alarm_info_dict):
    res_data = {}
    alarm_taper_shape_dict = spit_data_list(secondary_coil.childrenAlarmTaperShape, one=True)
    for key, alarmTaperShape in alarm_taper_shape_dict.items():
        alarmTaperShape: AlarmTaperShape
        if alarmTaperShape:
            alarmTaperShape: AlarmTaperShape
            res_data.update({
                key + "端 检测角度": alarmTaperShape.rotation_angle,
                key + "端 外圈最大值": alarmTaperShape.out_taper_max_value,
                key + "端 外圈最小值": alarmTaperShape.out_taper_min_value,
                key + "端 内圈最大值": alarmTaperShape.in_taper_max_value,
                key + "端 内圈最小值": alarmTaperShape.in_taper_min_value,
            })
            if alarm_info_dict[key]:
                alarm_info = alarm_info_dict[key]
                alarm_info: AlarmInfo
                res_data.update({
                    key + "端 塔形报警等级": alarm_info.taperShapeGrad,
                    key + "端 塔形报警信息": alarm_info.taperShapeMsg,
                })
    return res_data

def add_alarm_loose_info(secondary_coil,alarm_info_dict):
    res_data={}
    alarm_loose_coil_dict = spit_data_list(secondary_coil.childrenAlarmLooseCoil, one=True)
    for key, alarmLooseCoil in alarm_loose_coil_dict.items():
        if alarmLooseCoil:
            alarmLooseCoil:AlarmLooseCoil
            res_data.update({
                key+"端 松卷检测角度":alarmLooseCoil.rotation_angle,
                key+"端 松卷检测最宽":alarmLooseCoil.max_width
            })
            if alarm_info_dict[key]:
                alarm_info=alarm_info_dict[key]
                alarm_info:AlarmInfo
                res_data.update({
                    key+"端 松卷报警等级":alarm_info.looseCoilGrad,
                    key+"端 松卷报警信息":alarm_info.looseCoilMsg,
                })
    return res_data

def get_defects(secondary_coil:SecondaryCoil):
    return secondary_coil.childrenCoilDefect

def get_defect_data(secondary_coil:SecondaryCoil):
    res_data=OrderedDict()
    defect_list = secondary_coil.childrenCoilDefect
    defect_count_dict={"S":[],"L":[]}
    [defect_count_dict[d.surface].append(d) for d in defect_list]
    res_data.update({
        "S端 缺陷数":len(defect_count_dict["S"]),
        "L端 缺陷数量":len(defect_count_dict["L"]),
    })
    defect_dict = defaultdict(list)
    for defect in defect_list:
        defect:CoilDefect
        defect_dict[defect.defectName].append(defect)
    for k_,v_ in {
        "边裂":["烂边"],
        "刮丝":["刮丝"],
        "边部褶皱":["边部褶皱"],
        "折叠":["折叠"],
        "分层":["分层"]
    }.items():
        item_count=[]
        for defectName in defect_dict:
            if defectName in v_:
                item_count=item_count+defect_dict[defectName]
        res_data.update({
            k_:len(item_count),
            f"{k_}_报警":"是" if len(item_count)>0 else "否",
        })
    return res_data


def get_grad(alarm_info_dict):
    glob_grad = 1
    res_data = {}
    for key, value in alarm_info_dict.items():
        if value:
            alarm_info = alarm_info_dict[key]
            alarm_info: AlarmInfo
            if alarm_info.grad>glob_grad:
                glob_grad=alarm_info.grad
    res_data.update({
        "综合报警等级":glob_grad
    })
    # res_data.update({
    #     "灰度缩略图":"",
    #     "深度缩略图": "",
    # })
    return res_data


def get_item_data(secondary_coil:SecondaryCoil,export_config:ExportConfig=None):
    res_data={}
    alarm_info_dict={"S":None,"L":None}
    if export_config.export_header_data:
        res_data.update(get_header_data(secondary_coil))   # 添加 二级数据信息

    if export_config.export_plc_data:
        res_data.update(get_plc_data(secondary_coil))  # PLC 数据

    if export_config.export_alarm_info:
        res_data.update(get_alarm_info(secondary_coil,alarm_info_dict))

    if export_config.export_taper_shape_info:
        res_data.update(get_taper_shape_info(secondary_coil,alarm_info_dict))


    if export_config.export_alarm_loose:
        res_data.update(add_alarm_loose_info(secondary_coil, alarm_info_dict))

    if export_config.export_defect_data:
        res_data.update(get_defect_data(secondary_coil))



    # alarm_info_list = secondary_coil.childrenAlarmInfo
    # for alarm_info in alarm_info_list:
    #     alarm_info_dict[alarm_info.surface]=alarm_info
    return res_data