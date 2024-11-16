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
            spacing:5
            visible:listItemCoil.hasCoilData && listItemCoil.hasAlarmData
    // Rectangle{
    //     implicitWidth: 6
    //     implicitHeight: width
    //     radius: 3

    //     color: Status_S==-3?"black":Status_S==-2?"red":"green"
    // }
    // Rectangle{
    //     implicitWidth: 6
    //     implicitHeight: width
    //     radius: 3
    //     color: Status_L==-3?"black":Status_L==-2?"red":"green"
    // }
    AlarmRectangleItem{
        level:listItemCoil.flatRollGrad
    }
    AlarmRectangleItem{
    level:listItemCoil.taperShapeGrad
    }AlarmRectangleItem{
    level:listItemCoil.looseCoilGrad
    }AlarmRectangleItem{
    level:listItemCoil.defectGrad
    }

    }
}
