import QtQuick
import QtQuick.Controls.Material
Item{
    id:root
    width:height
    property color recColor:Material.color(Material.accentColor)

Rectangle{
    width: parent.width/3
    height: parent.height/3
    anchors.centerIn: parent
    border.width: 1
    color:recColor
}
}
