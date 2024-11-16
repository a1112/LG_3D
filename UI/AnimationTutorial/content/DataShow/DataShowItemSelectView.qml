import QtQuick
import QtQuick.Controls.Material
import "../Pages/Header"
Item{
    implicitWidth: 30

    Pane {
        anchors.fill: parent
        Material.elevation:6
    }
Rectangle{
    anchors.fill: parent
    color:"blue"
    opacity:0.1
}

Column{
    spacing: 5
CheckRec{
    text: "塔\n形\n曲\n线"
    height:100
    width:30
    fillWidth:true
    color:Material.color(Material.Teal)
}
CheckRec{
    text: "缺\n陷"
    height:50
    width:30
    fillWidth:true
    checkColor:"#00000000"
}
}
}
