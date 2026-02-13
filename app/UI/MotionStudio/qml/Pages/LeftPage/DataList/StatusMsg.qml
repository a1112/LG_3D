import QtQuick
import QtQuick.Controls.Material
Row {
    // 直接绑定到 listItemCoil.maxDefectName，避免手动同步
    property string maxDefectName: listItemCoil.maxDefectName || ""

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
            // 显示条件：有缺陷名称（从 API 的 maxDefectName 字段
            Label{
                visible: maxDefectName !== ""
                text: maxDefectName !== "" ? maxDefectName : ""
                font.pointSize: 9
                color: listItemCoil.defectNameColor  // 根据缺陷等级动态计算颜色
                font.bold: true
                font.family: "Microsoft YaHei"
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
