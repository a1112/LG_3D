import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import "../AlarmSimple"
Item {
    id:root
    required property var alarmInfo
    width:parent.width
    height:col.height

    readonly property bool hasFlatRollValue: root.alarmInfo.coreFlatRoll.innerDiameterMm > 0
    readonly property bool hasTaperValue: root.alarmInfo.coreTaperShape.s.hasData
                                          || root.alarmInfo.coreTaperShape.l.hasData
    readonly property bool hasLooseCoilValue: root.alarmInfo.coreLooseCoil.s.hasData
                                              || root.alarmInfo.coreLooseCoil.l.hasData

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
                value: root.hasFlatRollValue ? root.alarmInfo.coreFlatRoll.innerDiameterMm : -1
                displayValue: root.hasFlatRollValue
                              ? root.formatAlarmValue(root.alarmInfo.coreFlatRoll.innerDiameterMm, 0)
                              : "--"
                numericValue: root.hasFlatRollValue ? root.alarmInfo.coreFlatRoll.innerDiameterMm : 0
                height: 30
                level: root.alarmInfo.coreFlatRoll.alarmLevel
                toolTipText:"内径 < 680  mm 3级报警  当前值："
                            + (root.hasFlatRollValue
                               ? root.formatAlarmValue(root.alarmInfo.coreFlatRoll.innerDiameterMm, 1)
                               : "--")
            }
            SimpleValueAlarm{
                id: outerTaperAlarm
                width:col.width
                height: 30
                title:"外圈塔形:"
                value: root.hasTaperValue ? root.alarmInfo.coreTaperShape.outTaper : -1
                displayValue: root.hasTaperValue
                              ? root.formatAlarmValue(root.alarmInfo.coreTaperShape.outTaper, 0)
                              : "--"
                numericValue: root.hasTaperValue ? root.alarmInfo.coreTaperShape.outTaper : 0
                toolTipText:root.alarmInfo.coreTaperShape.str
                level: root.hasTaperValue ? (outerTaperAlarm.numericValue > 75 ? 3 : 1) : 0
            }
            SimpleValueAlarm{
                id: innerTaperAlarm
                width:col.width
                height: 30
                title:"内圈塔形:"
                value: root.hasTaperValue ? root.alarmInfo.coreTaperShape.innerTaper : -1
                displayValue: root.hasTaperValue
                              ? root.formatAlarmValue(root.alarmInfo.coreTaperShape.innerTaper, 0)
                              : "--"
                numericValue: root.hasTaperValue ? root.alarmInfo.coreTaperShape.innerTaper : 0
                toolTipText:"塔形 > 10 mm 3级报警  当前值："
                            + (root.hasTaperValue
                               ? root.formatAlarmValue(root.alarmInfo.coreTaperShape.innerTaper, 1)
                               : "--")
                level: root.hasTaperValue ? (innerTaperAlarm.numericValue > 10 ? 3 : 1) : 0
            }
            SimpleValueAlarm{
                width:col.width
                height: 30
                title:"松       卷:"
                value: root.hasLooseCoilValue ? root.alarmInfo.coreLooseCoil.max_width : -1
                displayValue: root.hasLooseCoilValue
                              ? root.formatAlarmValue(root.alarmInfo.coreLooseCoil.max_width, 0)
                              : "--"
                numericValue: root.hasLooseCoilValue ? root.alarmInfo.coreLooseCoil.max_width : 0
                toolTipText:"松卷最宽 > 25  mm 3级报警"
                level: root.alarmInfo.coreLooseCoil.alarmLevel
            }


        }
}
