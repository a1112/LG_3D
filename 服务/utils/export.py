import datetime
from CoilDataBase import Coil
from CoilDataBase.models import SecondaryCoil, AlarmFlatRoll, PlcData, CoilState, AlarmInfo, AlarmTaperShape, \
    AlarmLooseCoil
import xlsxwriter
import xlsxwriter
from io import BytesIO

def formatTime(time):
    time:datetime.datetime
    return time.strftime('%Y-%m-%d %H:%M:%S')

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

def getItemData(secondaryCoil:SecondaryCoil):
    resData={}

    resData.update({
        "流水号":secondaryCoil.Id,
        "卷号":secondaryCoil.CoilNo,
        "钢种":secondaryCoil.CoilType,
        "二级内径":secondaryCoil.CoilInside,
        "二级外径":secondaryCoil.CoilDia,
        "二级厚度":secondaryCoil.Thickness,
        "二级宽度":secondaryCoil.Width,
        "二级目标宽度":secondaryCoil.ActWidth,
        "二级数据接受时间":formatTime(secondaryCoil.CreateTime),
    }
    )
    plcDataList = secondaryCoil.childrenPlcData

    coilList = secondaryCoil.childrenCoil
    if coilList:
        coil=coilList[0]
        coil:Coil
        resData.update({
            "检测完成日期":formatTime(coil.DetectionTime),
        })
    if len(plcDataList):
        plcData=plcDataList[0]
        plcData:PlcData
        resData.update({
            "激光距离":plcData.location_laser,
            "S端移动位置":plcData.location_L,
            "L端移动位置":plcData.location_S,
        })

    coilStateList=secondaryCoil.childrenCoilState
    if len(coilStateList):
        coilState=coilStateList[0]
        coilState:CoilState
        resData.update({
            "X 标定":coilState.scan3dCoordinateScaleX,
            "Y 标定":coilState.scan3dCoordinateScaleY,
            "Z 标定":coilState.scan3dCoordinateScaleZ,
        })

    defectList = secondaryCoil.childrenCoilDefect
    defectDict={"S":[],"L":[]}
    [defectDict[d.surface].append(d) for d in defectList]
    resData.update({
        "S端 缺陷数":len(defectDict["S"]),
        "L端 缺陷数量":len(defectDict["L"]),
    })

    alarmInfoList = secondaryCoil.childrenAlarmInfo
    alarmInfoDict={"S":None,"L":None}
    for alarmInfo in alarmInfoList:
        alarmInfoDict[alarmInfo.surface]=alarmInfo

    alarmFlatRollList = secondaryCoil.childrenAlarmFlatRoll
    alarmFlatRollDict={"S":[],"L":[]}
    [alarmFlatRollDict[alarmFlatRoll.surface].append(alarmFlatRoll) for alarmFlatRoll in alarmFlatRollList]
    for key, value in alarmFlatRollDict.items():
        if len(value):
            alarmFlatRoll=value[0]
            alarmFlatRoll:AlarmFlatRoll
            resData.update({
                key + "端 检测外径":alarmFlatRoll.out_circle_width,
                key + "端 检测内径":alarmFlatRoll.inner_circle_width,
                # 更多参数
            })
            if alarmInfoDict[key]:
                alarmInfo=alarmInfoDict[key]
                alarmInfo:AlarmInfo
                resData.update({
                    key + "端 扁卷报警等级":alarmInfo.flatRollGrad,
                    key + "端 扁卷报警信息": alarmInfo.flatRollMsg,
                })
    alarmTaperShapeDict=spitDataList(secondaryCoil.childrenAlarmTaperShape,one = True)
    for key, value in alarmTaperShapeDict.items():
        if value:
            alarmTaperShape=value
            alarmTaperShape:AlarmTaperShape
            resData.update({
                key+"端 检测角度":alarmTaperShape.rotation_angle,
                key+"端 外圈最大值":alarmTaperShape.out_taper_max_value,
                key+"端 外圈最小值":alarmTaperShape.out_taper_min_value,
                key+"端 内圈最大值":alarmTaperShape.in_taper_max_value,
                key+"端 内圈最小值":alarmTaperShape.in_taper_min_value,
            })
            if alarmInfoDict[key]:
                alarmInfo=alarmInfoDict[key]
                alarmInfo:AlarmInfo
                resData.update({
                    key + "端 塔形报警等级":alarmInfo.taperShapeGrad,
                    key + "端 塔形报警信息": alarmInfo.taperShapeMsg,
                })
    alarmLooseCoilDict = spitDataList(secondaryCoil.childrenAlarmLooseCoil,one=True)



    for key, value in alarmLooseCoilDict.items():
        if value:
            alarmLooseCoil=value
            alarmLooseCoil:AlarmLooseCoil
            resData.update({
                key+"端 松卷检测角度":alarmLooseCoil.rotation_angle,
                key+"端 松卷检测最宽":alarmLooseCoil.max_width
            })
            if alarmInfoDict[key]:
                alarmInfo=alarmInfoDict[key]
                alarmInfo:AlarmInfo
                resData.update({
                    key+"端 松卷报警等级":alarmInfo.looseCoilGrad,
                    key+"端 松卷报警信息":alarmInfo.looseCoilMsg,
                })
    globGrad=1
    for key, value in alarmInfoDict.items():
        if value:
            alarmInfo = alarmInfoDict[key]
            alarmInfo: AlarmInfo
            if alarmInfo.grad>globGrad:
                globGrad=alarmInfo.grad
    resData.update({
        "综合报警等级":globGrad
    })
    resData.update({
        "灰度缩略图":"",
        "深度缩略图": "",
    })
    return resData

def exportDataByTime(startTime,endTime):
    output = BytesIO()

    # 将 BytesIO 对象传递给 xlsxwriter.Workbook
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()
    secondaryCoilList = Coil.getAllJoinDataByTime(startTime,endTime)
    dataAll=[]
    keyList=[]
    for secondaryCoil in secondaryCoilList:
        itemDict=getItemData(secondaryCoil)
        dataAll.append(itemDict)
        if len(itemDict.keys())>len(keyList):
            keyList=itemDict.keys()
    data = [keyList]
    for itemData in dataAll:
        row=[]
        for key in keyList:
            try:
                row.append(itemData[key])
            except:
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
    # 关闭 Workbook, 将数据写入 BytesIO
    workbook.close()
    file_size = output.getbuffer().nbytes
    # 重置 BytesIO 对象的读取位置
    output.seek(0)
    return output,file_size


def exportDataSimple(num=50,max=None):
    secondaryCoilList =  Coil.getAllJoinDataByNum(num,max)

    workbook = xlsxwriter.Workbook("数据导出测试.xlsx")
    worksheet = workbook.add_worksheet("完整数据表")

    dataAll=[]
    keyList=[]
    for secondaryCoil in secondaryCoilList:
        itemDict=getItemData(secondaryCoil)
        dataAll.append(itemDict)
        if len(itemDict.keys())>len(keyList):
            keyList=itemDict.keys()
    data = [keyList]
    for itemData in dataAll:
        row=[]
        for key in keyList:
            try:
                row.append(itemData[key])
            except:
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

    # 保存并关闭工作簿
    workbook.close()

if __name__ == '__main__':
    dt = exportDataSimple(1000,23060)
    print(dt)