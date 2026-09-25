import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

ItemDelegate {
    id:root
    required property var style
    property bool selected: false
    Material.foreground: selected ? root.style.accentColor : root.style.textColor
    Rectangle {
        width: parent.width-10
        anchors.horizontalCenter: parent.horizontalCenter
        height:root.selected? 2:0
        anchors.bottom: parent.bottom
        color: root.style.accentColor
    }
}
