import QtQuick 2.15

Item {
    property bool hasData:false
    property int secondaryCoilId:0
    property int alarmInfi_id:0
    property string nextCode:""
    property string nextName:""
    property int taperShapeGrad:0
    property int looseCoilGrad:0
    property int flatRollGrad:0
    property int defectGrad:0
    property int grad:0
    property string data:""
    property string surface:""
    property string taperShapeMsg:""
    property string looseCoilMsg:""
    property string flatRollMsg:""
    property string defectMsg:""
    property var createTime
    property var alarmTime:new Date()

    property var dataString:Qt.formatDateTime(alarmTime,"yyyy年MM月dd日")
    property var timeString:Qt.formatDateTime(alarmTime,"hh点mm分ss秒")


    property string alarmTimeString:Qt.formatDateTime(alarmTime,"yyyy_MM_dd hh_mm_ss")
    /*
{
                "secondaryCoilId": 23162,
                "Id": 259,
                "nextCode": "1",
                "nextName": "商品材",
                "taperShapeGrad": 2,
                "looseCoilGrad": 3,
                "flatRollGrad": 1,
                "defectGrad": 1,
                "grad": 3,
                "data": null,
                "surface": "L",
                "taperShapeMsg": "正常内径最高值 65.134 >= 60 检测角度180 \n",
                "looseCoilMsg": "松卷检测最宽 38.0 超过限制值 25",
                "flatRollMsg": "正常",
                "defectMsg": "",
                "crateTime": {
                    "year": 2024,
                    "month": 11,
                    "weekday": 1,
                    "day": 5,
                    "hour": 15,
                    "minute": 38,
                    "second": 32
                }
            }


    */
    function setAlarmInfo(alarmInfo){
        if (!alarmInfo) return
        hasData=true
        secondaryCoilId = alarmInfo.secondaryCoilId || 0
        nextCode = alarmInfo.nextCode || ""
        nextName = alarmInfo.nextName || ""
        taperShapeGrad = alarmInfo.taperShapeGrad || 0
        looseCoilGrad = alarmInfo.looseCoilGrad || 0
        flatRollGrad = alarmInfo.flatRollGrad || 0
        defectGrad = alarmInfo.defectGrad || 0
        grad = alarmInfo.grad || 0
        data = alarmInfo.data || ""
        surface = alarmInfo.surface || ""
        taperShapeMsg = alarmInfo.taperShapeMsg || ""
        looseCoilMsg = alarmInfo.looseCoilMsg || ""
        flatRollMsg = alarmInfo.flatRollMsg || ""
        defectMsg = alarmInfo.defectMsg || ""
        // 兼容 createTime 和 crateTime 两种字段名
        createTime = alarmInfo.createTime || alarmInfo.crateTime || {}
        // alarmTime = new Date(createTime["year"],createTime["month"]-1,createTime["day"],
        //                     createTime["hour"],createTime["minute"],createTime["second"])
    }
}
