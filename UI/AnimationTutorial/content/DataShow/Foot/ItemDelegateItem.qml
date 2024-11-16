import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

ItemDelegate {
    id:root
    property bool selected: false
    Material.foreground:selected? Material.accent: Material.text
    Rectangle {
        width: parent.width-10
        anchors.horizontalCenter: parent.horizontalCenter
        height:root.selected? 2:0
        anchors.bottom: parent.bottom
        color: Material.color(Material.accent)
    }
}
