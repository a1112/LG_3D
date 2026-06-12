import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
Row {
    // 直接绑定到 listItemCoil.maxDefectName，避免手动同步
    property string maxDefectName: listItemCoil.maxDefectName || ""
    property int defectCount: coilModel ? coilModel.coilDefectCountTotal : 0
    property int defectCountS: coilModel ? coilModel.coilDefectCountS : 0
    property int defectCountL: coilModel ? coilModel.coilDefectCountL : 0
    property string defectStatusTip: "S: " + defectCountS
                                    + "  L: " + defectCountL
                                    + (maxDefectName ? "\n最严重缺陷: " + maxDefectName : "")

    spacing:1
    Label{
        visible:!listItemCoil.hasCoilData
        text: listItemCoil.nullCoilString
        color:Material.color(Material.Amber)
        font.bold:true
        font.family:"Microsoft YaHei"
    }

    Label{
        visible: !listItemCoil.hasAlarmData
        text: listItemCoil.nullAlarmString
        color: Material.color(Material.Lime)
        font.bold: true
        font.family: "Microsoft YaHei"
    }

    Row{
        spacing:1
        Label{
            visible: listItemCoil.hasCoilData
            text: defectCount + ""
            font.pointSize: 11
            color: defectCount > 0 ? listItemCoil.defectNameColor : Material.color(Material.Lime)
            font.bold: true
            font.family: "Microsoft YaHei"
            ToolTip.visible: ma.containsMouse
            ToolTip.text: defectStatusTip
            MouseArea {
                id: ma
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.NoButton
            }
        }
        Label {
            visible: listItemCoil.hasCoilData && defectCount > 0 && maxDefectName.length > 0
            width: Math.min(90, implicitWidth)
            text: maxDefectName
            elide: Text.ElideRight
            font.pointSize: 9
            color: listItemCoil.defectNameColor
            font.bold: true
            font.family: "Microsoft YaHei"
            ToolTip.visible: maxDefectMa.containsMouse
            ToolTip.text: defectStatusTip
            MouseArea {
                id: maxDefectMa
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.NoButton
            }
        }
        AlarmRectangleItem{
            anchors.verticalCenter:parent.verticalCenter
            level:Math.max(
                      listItemCoil.flatRollGrad,
                      listItemCoil.taperShapeGrad,
                      listItemCoil.looseCoilGrad,
                      listItemCoil.defectGrad
                      )
        }
    }
}
