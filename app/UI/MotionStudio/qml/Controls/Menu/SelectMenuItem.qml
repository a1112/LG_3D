import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
MenuItem {
    id:root
    property var style
    property bool selectd:false
    property color selectdColor: Material.color(Material.Orange)

    Material.foreground: root.selectd
                         ? root.selectdColor
                         : root.style ? root.style.textColor : palette.text
    Rectangle{
        anchors.fill: parent
        color:"#00000000"
        border.color:root.selectd?Material.color(Material.Orange):"#00000000"
        border.width:2
    }
}
