import QtQuick 2.15

Item{
    anchors.right: parent.right
    height:parent.height
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
