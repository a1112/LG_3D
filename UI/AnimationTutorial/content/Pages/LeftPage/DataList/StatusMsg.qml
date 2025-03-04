import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
Row {

    spacing:5
    Label{
        visible:!listItemCoil.hasCoilData
        text: listItemCoil.nullCoilString
        color:Material.color(Material.Amber)
        font.bold:true
        font.family:"Microsoft YaHei"
    }
    Label{
        visible:!listItemCoil.hasAlarmData
        text: listItemCoil.nullAlarmString
        color:Material.color(Material.Lime)
        font.bold:true
        font.family:"Microsoft YaHei"
    }
    Row{
            spacing:10
            visible:listItemCoil.hasCoilData && listItemCoil.hasAlarmData

            Label{
                text: coilModel.maxDefect.defectName
                font.pointSize:9
                color:  coilModel.defectErrorColor  //Material.color(Material.Green)
                font.bold:true
                font.family:"Microsoft YaHei"
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

    // AlarmRectangleItem{
    //     level:listItemCoil.flatRollGrad
    // }
    // AlarmRectangleItem{
    // level:listItemCoil.taperShapeGrad
    // }AlarmRectangleItem{
    // level:listItemCoil.looseCoilGrad
    // }AlarmRectangleItem{
    // level:listItemCoil.defectGrad
    // }

    }
}
