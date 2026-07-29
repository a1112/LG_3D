import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
Row {
    id: root
    required property var coilModel
    required property var summary

    readonly property string maxDefectName: root.summary.maxDefectName || ""
    readonly property string maxDefectSurface: root.summary.maxDefectSurface || ""
    readonly property int maxDefectLevel: root.summary.maxDefectLevel || 0
    readonly property int defectCount: root.coilModel ? root.coilModel.coilDefectCountTotal : 0
    readonly property int defectCountS: root.coilModel ? root.coilModel.coilDefectCountS : 0
    readonly property int defectCountL: root.coilModel ? root.coilModel.coilDefectCountL : 0
    readonly property bool hasMaxDefectName: root.maxDefectName.length > 0
    readonly property string maxDefectLabel: root.hasMaxDefectName
                                    ? ((root.maxDefectSurface ? root.maxDefectSurface + ":" : "")
                                       + root.maxDefectName)
                                    : ""
    readonly property string statusText: root.hasMaxDefectName
        ? root.defectCount + " / " + root.maxDefectLabel : String(root.defectCount)
    readonly property int statusMinimumWidth:
        root.summary.hasCoilData && root.defectCount > 0
        && root.hasMaxDefectName ? 150 : 34
    readonly property string defectStatusTip: "S: " + root.defectCountS
                                    + "  L: " + root.defectCountL
                                    + (root.maxDefectName ? "\n最严重缺陷: " + root.maxDefectName : "")
                                    + (root.maxDefectSurface ? " (" + root.maxDefectSurface + ")" : "")
                                    + (root.maxDefectLevel > 0 ? "  等级: " + root.maxDefectLevel : "")

    Layout.minimumWidth: root.statusMinimumWidth
    Layout.preferredWidth: root.summary.hasCoilData
                           ? Math.min(230, Math.max(root.statusMinimumWidth,
                                                    statusTextLabel.implicitWidth + 22))
                           : implicitWidth
    Layout.maximumWidth: 250
    clip: true
    spacing:1
    Label{
        visible:!root.summary.hasCoilData
        text: root.summary.nullCoilString
        color:Material.color(Material.Amber)
        font.bold:true
        font.family:"Microsoft YaHei"
    }

    Label{
        visible: !root.summary.hasAlarmData
        text: root.summary.nullAlarmString
        color: Material.color(Material.Lime)
        font.bold: true
        font.family: "Microsoft YaHei"
    }

    Row{
        spacing:4
        Label{
            id: statusTextLabel
            visible: root.summary.hasCoilData
            width: Math.min(225, implicitWidth)
            text: root.statusText
            elide: Text.ElideRight
            font.pointSize: 11
            color: root.defectCount > 0
                   ? root.summary.defectNameColor : Material.color(Material.Lime)
            font.bold: true
            font.family: "Microsoft YaHei"
            ToolTip.visible: ma.containsMouse
            ToolTip.text: root.defectStatusTip
            MouseArea {
                id: ma
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.NoButton
            }
        }
        AlarmRectangleItem{
            anchors.verticalCenter:parent.verticalCenter
            level:Math.max(
                      root.summary.flatRollGrad,
                      root.summary.taperShapeGrad,
                      root.summary.looseCoilGrad,
                      root.summary.defectGrad
                      )
        }
    }
}
