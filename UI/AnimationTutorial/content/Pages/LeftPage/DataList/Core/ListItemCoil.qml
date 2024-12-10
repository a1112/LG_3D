import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
Item {

    property bool hasAlarmData:true// hasAlarmInfo
    property bool hasCoilData: hasCoil

    function level2Color(level){
        if(level<=1){
            return Material.color(Material.Green)
        }else if(level==2){
            return Material.color(Material.Orange)
        }else if(level>=3){
            return Material.color(Material.Red)
        }
    }
    function level2Source(level){
        return ""
        if(level<=1){
            return ""
        }else if(level==2){
            return "../../../icons/warning_1.png"
        }else if(level>=3){
            return "../../../icons/warning_1.png"
        }

    }

    property string nullCoilString: "无数据"
    property string nullAlarmString: "未识别"
    property string detectionStatuColor:
        !hasCoilData?Material.color(Material.Grey):
        !hasAlarmData?Material.color(Material.Yellow):
        "#5AEDFF"

    property ListModel alarmNodel:
    ListModel{
    }

    property int defectGrad:Math.max(alarmInfoItemS.defectGrad,alarmInfoItemL.defectGrad)
    property int grad:Math.max(alarmInfoItemS.grad,alarmInfoItemL.grad)
    property int taperShapeGrad:Math.max(alarmInfoItemS.taperShapeGrad,alarmInfoItemL.taperShapeGrad)
    property int looseCoilGrad:Math.max(alarmInfoItemS.looseCoilGrad,alarmInfoItemL.looseCoilGrad)
    property int flatRollGrad:Math.max(alarmInfoItemS.flatRollGrad,alarmInfoItemL.flatRollGrad)

    property string defectMsg:"S: "+alarmInfoItemS.defectMsg+"\nL: "+alarmInfoItemL.defectMsg
    property string taperShapeMsg:"S: "+alarmInfoItemS.taperShapeMsg+"\nL: "+alarmInfoItemL.taperShapeMsg
    property string looseCoilMsg:"S: "+alarmInfoItemS.looseCoilMsg+"\nL: "+alarmInfoItemL.looseCoilMsg
    property string flatRollMsg:"S: "+alarmInfoItemS.flatRollMsg+"\nL: "+alarmInfoItemL.flatRollMsg

    property string errorMsg: "扁卷:\n"+flatRollMsg+"\n塔形\n"+taperShapeMsg+"\n松卷:\n"+looseCoilMsg+"\n缺陷:\n"+defectMsg

    property AlarmInfoItem alarmInfoItemS: AlarmInfoItem{
        data:AlarmInfo["S"]
    }

    property AlarmInfoItem alarmInfoItemL: AlarmInfoItem{
        data:AlarmInfo["L"]
    }
    Component.onCompleted:{
        alarmNodel.clear()

        let keyList=[]
        for (let key in AlarmInfo) {
            keyList.push(key)
        }

        for (let key in AlarmInfo) {
            let item=AlarmInfo[key]
            for(let itemKey in item){
                keyList.forEach((key_)=>{
                                })

            }
            break

        }
    }

    property var testData:    {
        "hasCoil": true,
        "hasAlarmInfo": true,
        "DefectCountS": 0,
        "Id": 23053,
        "DefectCountL": 0,
        "Status_L": 0,
        "Grade": 0,
        "SecondaryCoilId": 23053,
        "DetectionTime": {
            "year": 2024,
            "month": 11,
            "weekday": 4,
            "day": 1,
            "hour": 16,
            "minute": 49,
            "second": 14
        },
        "CheckStatus": 0,
        "Status_S": 0,
        "Msg": "",
        "AlarmInfo": {
            "L": {
                "nextCode": "2",
                "secondaryCoilId": 23053,
                "Id": 41,
                "nextName": "冷轧基板",
                "taperShapeGrad": 2,
                "looseCoilGrad": 1,
                "flatRollGrad": 1,
                "defectGrad": 1,
                "grad": 2,
                "data": null,
                "surface": "L",
                "taperShapeMsg": "正常内径最高值 63.045618659850106 >= 60 检测角度180 \n",
                "looseCoilMsg": "",
                "flatRollMsg": "正常",
                "defectMsg": "",
                "crateTime": {
                    "year": 2024,
                    "month": 11,
                    "weekday": 4,
                    "day": 1,
                    "hour": 16,
                    "minute": 49,
                    "second": 11
                }
            },
            "S": {
                "nextCode": "2",
                "secondaryCoilId": 23053,
                "Id": 42,
                "nextName": "冷轧基板",
                "taperShapeGrad": 1,
                "looseCoilGrad": 1,
                "flatRollGrad": 1,
                "defectGrad": 1,
                "grad": 1,
                "data": null,
                "surface": "S",
                "taperShapeMsg": "正常",
                "looseCoilMsg": "",
                "flatRollMsg": "正常",
                "defectMsg": "",
                "crateTime": {
                    "year": 2024,
                    "month": 11,
                    "weekday": 4,
                    "day": 1,
                    "hour": 16,
                    "minute": 49,
                    "second": 12
                }
            }
        },
        "Thickness": 2.9,
        "Width": 1273,
        "Weight": 50,
        "ActWidth": 1288,
        "CoilType": "DX51D-2",
        "CreateTime": {
            "year": 2024,
            "month": 10,
            "weekday": 3,
            "day": 17,
            "hour": 23,
            "minute": 21,
            "second": 1
        },
        "CoilNo": "4V08312800",
        "CoilInside": 762,
        "CoilDia": 1936,
        "childrenCoil": [
            {
                "DefectCountS": 0,
                "Id": 42827,
                "DefectCountL": 0,
                "Status_L": 0,
                "Grade": 0,
                "SecondaryCoilId": 23053,
                "DetectionTime": {
                    "year": 2024,
                    "month": 11,
                    "weekday": 4,
                    "day": 1,
                    "hour": 16,
                    "minute": 49,
                    "second": 14
                },
                "CheckStatus": 0,
                "Status_S": 0,
                "Msg": ""
            }
        ],
        "childrenAlarmInfo": [
            {
                "nextCode": "2",
                "secondaryCoilId": 23053,
                "Id": 41,
                "nextName": "冷轧基板",
                "taperShapeGrad": 2,
                "looseCoilGrad": 1,
                "flatRollGrad": 1,
                "defectGrad": 1,
                "grad": 2,
                "data": null,
                "surface": "L",
                "taperShapeMsg": "正常内径最高值 63.045618659850106 >= 60 检测角度180 \n",
                "looseCoilMsg": "",
                "flatRollMsg": "正常",
                "defectMsg": "",
                "crateTime": {
                    "year": 2024,
                    "month": 11,
                    "weekday": 4,
                    "day": 1,
                    "hour": 16,
                    "minute": 49,
                    "second": 11
                }
            },
            {
                "nextCode": "2",
                "secondaryCoilId": 23053,
                "Id": 42,
                "nextName": "冷轧基板",
                "taperShapeGrad": 1,
                "looseCoilGrad": 1,
                "flatRollGrad": 1,
                "defectGrad": 1,
                "grad": 1,
                "data": null,
                "surface": "S",
                "taperShapeMsg": "正常",
                "looseCoilMsg": "",
                "flatRollMsg": "正常",
                "defectMsg": "",
                "crateTime": {
                    "year": 2024,
                    "month": 11,
                    "weekday": 4,
                    "day": 1,
                    "hour": 16,
                    "minute": 49,
                    "second": 12
                }
            }
        ],
        "NextCode": "2",
        "NextInfo": "冷轧基板"
    }

}
