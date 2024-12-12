import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import "../AlarmSimple"
Item {
    id:root
    width:parent.width
    height:col.height
    Frame{
        anchors.fill: parent
    }
        Column{
            id:col
            width:root.width
            SimpleValueAlarm{
                width:col.width
                title:"内       径:"
                value:(coreAlarmInfo.coreFlatRoll.innerDiameter* coreModel.surfaceS.scan3dScaleX).toFixed(0)
                height: 30
                level: coreAlarmInfo.coreFlatRoll.alarmLevel
                toolTipText:"内径 < 680  mm 3级报警  当前值：" +coreAlarmInfo.coreFlatRoll.innerDiameter
            }
            SimpleValueAlarm{
                width:col.width
                height: 30
                title:"外圈塔形:"
                value:coreAlarmInfo.coreTaperShape.outTaper.toFixed(0)
                toolTipText:coreAlarmInfo.coreTaperShape.str //"塔形 > 75 mm 3级报警  当前值："+coreAlarmInfo.coreTaperShape.outTaper
                level: value>75? 3 : 1
            }
            SimpleValueAlarm{
                width:col.width
                height: 30
                title:"内圈塔形:"
                value:coreAlarmInfo.coreTaperShape.innerTaper.toFixed(0)
                toolTipText:"塔形 > 10 mm 3级报警  当前值："+coreAlarmInfo.coreTaperShape.innerTaper
                level: value>75? 3 : 1
            }
            SimpleValueAlarm{
                width:col.width
                height: 30
                title:"松       卷:"
                value:coreAlarmInfo.coreLooseCoil.max_width
                toolTipText:"松卷最宽 > 25  mm 3级报警"
                level: value>=10? 3 : 1
            }


        }
}
