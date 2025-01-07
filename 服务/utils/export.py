from io import BytesIO
import datetime
from collections import OrderedDict,defaultdict
import xlsxwriter

from CoilDataBase import Coil
from CoilDataBase.models import AlarmFlatRoll, CoilDefect
from CoilDataBase.models import PlcData
from CoilDataBase.models import CoilState
from CoilDataBase.models import SecondaryCoil
from CoilDataBase.models import AlarmTaperShape
from CoilDataBase.models import AlarmLooseCoil
from CoilDataBase.models import AlarmInfo
import Globs

def format_time(time):
    time:datetime.datetime
    return time.strftime(Globs.control.exportTimeFormat)

def spitDataList(dataList,one=False):
    defectDict={"S":[],"L":[]}
    [defectDict[data.surface].append(data) for data in dataList ]
    if one:
        for key in defectDict.keys():
            if len(defectDict[key])>=1:
                defectDict[key]=defectDict[key][0]
            else:
                defectDict[key]=None
    return defectDict

def get_item_header_data(secondary_coil:SecondaryCoil):
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
def get_item_plc_data(secondary_coil:SecondaryCoil):
    plc_data_list = secondary_coil.childrenPlcData

    if len(plc_data_list):
        plc_data=plc_data_list[0]
        plc_data:PlcData
        return {
            "激光距离":plc_data.location_laser,
            "S端移动位置":plc_data.location_L,
            "L端移动位置":plc_data.location_S,
        }

def get_item_defect_data(secondary_coil:SecondaryCoil):
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


def get_item_data(secondary_coil:SecondaryCoil,export_type="3D"):
    res_data={}
    res_data.update(get_item_header_data(secondary_coil))   # 添加 二级数据信息
    if export_type=="all":
        res_data.update(get_item_plc_data(secondary_coil))  # PLC 数据


    coil_state_list=secondary_coil.childrenCoilState
    if len(coil_state_list):
        coil_state=coil_state_list[0]
        coil_state:CoilState
        res_data.update({
            "X 标定":coil_state.scan3dCoordinateScaleX,
            "Y 标定":coil_state.scan3dCoordinateScaleY,
            "Z 标定":coil_state.scan3dCoordinateScaleZ,
        })

    alarm_info_list = secondary_coil.childrenAlarmInfo
    alarm_info_dict={"S":None,"L":None}
    for alarmInfo in alarm_info_list:
        alarm_info_dict[alarmInfo.surface]=alarmInfo

    alarm_flat_roll_list = secondary_coil.childrenAlarmFlatRoll
    alarm_flat_roll_dict={"S":[],"L":[]}
    [alarm_flat_roll_dict[alarmFlatRoll.surface].append(alarmFlatRoll) for alarmFlatRoll in alarm_flat_roll_list]
    for key, value in alarm_flat_roll_dict.items():
        if len(value):
            alarmFlatRoll=value[0]
            alarmFlatRoll:AlarmFlatRoll
            res_data.update({
                key + "端 检测外径":alarmFlatRoll.out_circle_width,
                key + "端 检测内径":alarmFlatRoll.inner_circle_width,
                # 更多参数
            })
            if alarm_info_dict[key]:
                alarmInfo=alarm_info_dict[key]
                alarmInfo:AlarmInfo
                res_data.update({
                    key + "端 扁卷报警等级":alarmInfo.flatRollGrad,
                    key + "端 扁卷报警信息": alarmInfo.flatRollMsg,
                })
    alarmTaperShapeDict=spitDataList(secondary_coil.childrenAlarmTaperShape, one = True)
    for key, alarmTaperShape in alarmTaperShapeDict.items():
        alarmTaperShape:AlarmTaperShape
        if alarmTaperShape:
            alarmTaperShape:AlarmTaperShape
            res_data.update({
                key+"端 检测角度":alarmTaperShape.rotation_angle,
                key+"端 外圈最大值":alarmTaperShape.out_taper_max_value,
                key+"端 外圈最小值":alarmTaperShape.out_taper_min_value,
                key+"端 内圈最大值":alarmTaperShape.in_taper_max_value,
                key+"端 内圈最小值":alarmTaperShape.in_taper_min_value,
            })
            if alarm_info_dict[key]:
                alarmInfo=alarm_info_dict[key]
                alarmInfo:AlarmInfo
                res_data.update({
                    key + "端 塔形报警等级":alarmInfo.taperShapeGrad,
                    key + "端 塔形报警信息": alarmInfo.taperShapeMsg,
                })


    alarm_loose_coil_dict = spitDataList(secondary_coil.childrenAlarmLooseCoil, one=True)
    for key, alarmLooseCoil in alarm_loose_coil_dict.items():
        if alarmLooseCoil:
            alarmLooseCoil:AlarmLooseCoil
            res_data.update({
                key+"端 松卷检测角度":alarmLooseCoil.rotation_angle,
                key+"端 松卷检测最宽":alarmLooseCoil.max_width
            })
            if alarm_info_dict[key]:
                alarmInfo=alarm_info_dict[key]
                alarmInfo:AlarmInfo
                res_data.update({
                    key+"端 松卷报警等级":alarmInfo.looseCoilGrad,
                    key+"端 松卷报警信息":alarmInfo.looseCoilMsg,
                })
    globGrad=1
    for key, value in alarm_info_dict.items():
        if value:
            alarmInfo = alarm_info_dict[key]
            alarmInfo: AlarmInfo
            if alarmInfo.grad>globGrad:
                globGrad=alarmInfo.grad
    res_data.update({
        "综合报警等级":globGrad
    })
    res_data.update({
        "灰度缩略图":"",
        "深度缩略图": "",
    })
    if export_type in ["all","defect"]:
        res_data.update(get_item_defect_data(secondary_coil))   # 提起缺陷

    return res_data

def export_data_by_coil_id_list(coil_id_list,worksheet,export_type="3D"):
    data_all = []
    key_list = []

    for secondaryCoil in coil_id_list:
        item_dict = get_item_data(secondaryCoil,export_type)
        data_all.append(item_dict)
        if len(item_dict.keys()) > len(key_list):
            key_list = item_dict.keys()
    data = [key_list]
    for itemData in data_all:
        row=[]
        for key in key_list:
            try:
                row.append(itemData[key])
            except (Exception,) as e:
                print(e)
                row.append("")
        data.append(row)


    # 写入数据
    for row_num, row_data in enumerate(data):
        worksheet.write_row(row_num, 0, row_data)
    # 添加表格格式
    worksheet.add_table(
        0, 0, len(data) - 1, len(data[0]) - 1,  # 表格的范围
        {
            "columns": [{"header": col} for col in data[0]],  # 设置表头
            "style": "Table Style Medium 9",  # 表格样式
            "autofilter": True,  # 启用自动筛选
        }
    )

def export_data_by_time(start_time, end_time, export_type="3D"):
    output = BytesIO()

    # 将 BytesIO 对象传递给 xlsxwriter.Workbook
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()
    secondary_coil_list = Coil.getAllJoinDataByTime(start_time, end_time)
    export_data_by_coil_id_list(secondary_coil_list, worksheet, export_type)
    workbook.close()
    file_size = output.getbuffer().nbytes
    # 重置 BytesIO 对象的读取位置
    output.seek(0)
    return output,file_size


def export_data_simple(num=50, max_coil=None, export_type="3D"):
    secondary_coil_list =  Coil.getAllJoinDataByNum(num, max_coil)

    workbook = xlsxwriter.Workbook("数据导出测试.xlsx")

    if export_type=="3D":
        worksheet = workbook.add_worksheet("完整数据表")
        export_data_by_coil_id_list(secondary_coil_list, worksheet, export_type)
        worksheet.close()
    if export_type == "defect":
        worksheet = workbook.add_worksheet("缺陷数据导出")
        export_data_by_coil_id_list(secondary_coil_list, worksheet, export_type)
    workbook.close()


if __name__ == '__main__':
    dt = export_data_simple(40000, 41000,export_type="defect")
    print(dt)