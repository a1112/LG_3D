import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import "../AlarmSimple"
Item {
    id:root
    width:parent.width
    height:col.height

    readonly property bool hasFlatRollValue: coreAlarmInfo.coreFlatRoll.innerDiameterMm > 0
    readonly property bool hasTaperValue: coreAlarmInfo.coreTaperShape.s.hasData || coreAlarmInfo.coreTaperShape.l.hasData
    readonly property bool hasLooseCoilValue: coreAlarmInfo.coreLooseCoil.s.hasData || coreAlarmInfo.coreLooseCoil.l.hasData

    function formatAlarmValue(value, decimals) {
        let numberValue = Number(value)
        return isFinite(numberValue) ? numberValue.toFixed(decimals) : "--"
    }
    Frame{
        anchors.fill: parent
    }
        Column{
            id:col
            width:root.width
            SimpleValueAlarm{
                width:col.width
                title:"内       径:"
                value: root.hasFlatRollValue ? coreAlarmInfo.coreFlatRoll.innerDiameterMm : -1
                displayValue: root.hasFlatRollValue ? root.formatAlarmValue(coreAlarmInfo.coreFlatRoll.innerDiameterMm, 0) : "--"
                numericValue: root.hasFlatRollValue ? coreAlarmInfo.coreFlatRoll.innerDiameterMm : 0
                height: 30
                level: coreAlarmInfo.coreFlatRoll.alarmLevel
                toolTipText:"内径 < 680  mm 3级报警  当前值：" +(root.hasFlatRollValue ? root.formatAlarmValue(coreAlarmInfo.coreFlatRoll.innerDiameterMm, 1) : "--")
            }
            SimpleValueAlarm{
                width:col.width
                height: 30
                title:"外圈塔形:"
                value: root.hasTaperValue ? coreAlarmInfo.coreTaperShape.outTaper : -1
                displayValue: root.hasTaperValue ? root.formatAlarmValue(coreAlarmInfo.coreTaperShape.outTaper, 0) : "--"
                numericValue: root.hasTaperValue ? coreAlarmInfo.coreTaperShape.outTaper : 0
                toolTipText:coreAlarmInfo.coreTaperShape.str //"塔形 > 75 mm 3级报警  当前值："+coreAlarmInfo.coreTaperShape.outTaper
                level: root.hasTaperValue ? (numericValue > 75 ? 3 : 1) : 0
            }
            SimpleValueAlarm{
                width:col.width
                height: 30
                title:"内圈塔形:"
                value: root.hasTaperValue ? coreAlarmInfo.coreTaperShape.innerTaper : -1
                displayValue: root.hasTaperValue ? root.formatAlarmValue(coreAlarmInfo.coreTaperShape.innerTaper, 0) : "--"
                numericValue: root.hasTaperValue ? coreAlarmInfo.coreTaperShape.innerTaper : 0
                toolTipText:"塔形 > 10 mm 3级报警  当前值："+(root.hasTaperValue ? root.formatAlarmValue(coreAlarmInfo.coreTaperShape.innerTaper, 1) : "--")
                level: root.hasTaperValue ? (numericValue > 10 ? 3 : 1) : 0
            }
            SimpleValueAlarm{
                width:col.width
                height: 30
                title:"松       卷:"
                value: root.hasLooseCoilValue ? coreAlarmInfo.coreLooseCoil.max_width : -1
                displayValue: root.hasLooseCoilValue ? root.formatAlarmValue(coreAlarmInfo.coreLooseCoil.max_width, 0) : "--"
                numericValue: root.hasLooseCoilValue ? coreAlarmInfo.coreLooseCoil.max_width : 0
                toolTipText:"松卷最宽 > 25  mm 3级报警"
                level: coreAlarmInfo.coreLooseCoil.alarmLevel
            }


        }
}
