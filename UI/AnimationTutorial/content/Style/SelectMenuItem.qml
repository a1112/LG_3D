import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
MenuItem {
    id:root
    property bool selectd:false
    Material.foreground:root.selectd?Material.color(Material.Orange):coreStyle.textColor
    Rectangle{
        anchors.fill: parent
        color:"#00000000"
        border.color:root.selectd?Material.color(Material.Orange):"#00000000"
        border.width:2
    }
}
