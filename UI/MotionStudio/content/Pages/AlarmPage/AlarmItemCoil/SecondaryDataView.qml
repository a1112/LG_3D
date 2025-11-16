import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../AlarmSimple"
Item {
    id:root
    width:parent.width
    height:col.height
    Frame{
        anchors.fill: parent
    }
Row{
    id:row
    width:parent.width

    spacing: 10
    Label{
        id:titleLabel
        text:"二\n级"
        font.pointSize: 14
        font.bold: true
        color: Material.color(Material.Yellow)
        font.family: "Microsoft YaHei"
        anchors.verticalCenter: col.verticalCenter
    }
    Column{
        id:col
        width:root.width-titleLabel.width
        SimpleValueRow{
            width:col.width
            title:"内径"
            value:core.currentCoilModel.coilInside
    height: 30
        }
        SimpleValueRow{
            width:col.width
            height: 30
            title:"外径"
            value:core.currentCoilModel.coilDia
        }
    }
}



}
