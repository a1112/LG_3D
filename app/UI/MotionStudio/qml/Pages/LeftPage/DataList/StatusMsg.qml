import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
Row {
    // 直接绑定到 listItemCoil.maxDefectName，避免手动同步
    property string maxDefectName: listItemCoil.maxDefectName || ""
    property int defectCount: coilModel ? coilModel.coilDefectCountTotal : 0

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
            ToolTip.text: "S: " + coilModel.coilDefectCountS + "  L: " + coilModel.coilDefectCountL
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
                      listItemCoil.flatRollGrad,
                      listItemCoil.taperShapeGrad,
                      listItemCoil.looseCoilGrad,
                      listItemCoil.defectGrad
                      )
        }
    }
}
