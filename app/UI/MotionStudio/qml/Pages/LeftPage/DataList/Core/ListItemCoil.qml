import QtQuick
import QtQuick.Controls.Material

QtObject {
    id: root

    required property var style

    property bool hasCoil: true
    property var alarmInfo: null
    property string maxDefectName: ""
    property int maxDefectLevel: 0
    property string maxDefectSurface: ""

    readonly property bool hasAlarmData: Boolean(alarmInfo && (alarmInfo.S || alarmInfo.L))
    readonly property bool hasCoilData: hasCoil
    readonly property color defectNameColor: defectLevel2Color(maxDefectLevel)

    readonly property string nullCoilString: qsTr("无数据")
    readonly property string nullAlarmString: qsTr("未识别")
    readonly property color detectionStatuColor: !hasCoilData
                                                   ? style.labelColor
                                                   : !hasAlarmData
                                                     ? style.statusWarningColor
                                                     : style.statusSuccessColor

    function defectLevel2Color(level) {
        if (level <= 0) {
            return style.statusSuccessColor
        }
        if (level <= 2) {
            return Material.color(Material.LightBlue)
        }
        if (level === 3) {
            return style.statusWarningColor
        }
        return style.statusErrorColor
    }

    function level2Color(level) {
        if (level <= 1) {
            return style.statusSuccessColor
        }
        if (level === 2) {
            return style.statusWarningColor
        }
        return style.statusErrorColor
    }

    function level2Source(level) {
        return level > 1 ? style.getIcon("warning_1") : ""
    }

    property AlarmInfoItem alarmInfoItemS: AlarmInfoItem {
        data: root.alarmInfo && root.alarmInfo.S ? root.alarmInfo.S : null
    }
    property AlarmInfoItem alarmInfoItemL: AlarmInfoItem {
        data: root.alarmInfo && root.alarmInfo.L ? root.alarmInfo.L : null
    }

    readonly property int defectGrad: Math.max(alarmInfoItemS.defectGrad, alarmInfoItemL.defectGrad)
    readonly property int grad: Math.max(alarmInfoItemS.grad, alarmInfoItemL.grad)
    readonly property int taperShapeGrad: Math.max(alarmInfoItemS.taperShapeGrad, alarmInfoItemL.taperShapeGrad)
    readonly property int looseCoilGrad: Math.max(alarmInfoItemS.looseCoilGrad, alarmInfoItemL.looseCoilGrad)
    readonly property int flatRollGrad: Math.max(alarmInfoItemS.flatRollGrad, alarmInfoItemL.flatRollGrad)

    readonly property string defectMsg: "S: " + alarmInfoItemS.defectMsg + "\nL: " + alarmInfoItemL.defectMsg
    readonly property string taperShapeMsg: "S: " + alarmInfoItemS.taperShapeMsg + "\nL: " + alarmInfoItemL.taperShapeMsg
    readonly property string looseCoilMsg: "S: " + alarmInfoItemS.looseCoilMsg + "\nL: " + alarmInfoItemL.looseCoilMsg
    readonly property string flatRollMsg: "S: " + alarmInfoItemS.flatRollMsg + "\nL: " + alarmInfoItemL.flatRollMsg
    readonly property string errorMsg: qsTr("扁卷:\n") + flatRollMsg
                                       + qsTr("\n塔形:\n") + taperShapeMsg
                                       + qsTr("\n松卷:\n") + looseCoilMsg
                                       + qsTr("\n缺陷:\n") + defectMsg
}
