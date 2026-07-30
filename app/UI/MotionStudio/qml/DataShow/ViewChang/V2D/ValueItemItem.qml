import QtQuick
import QtQuick.Controls

Item {
    id: root

    required property real rowHeight
    required property string valueText

    width: 35
    height: root.rowHeight

    Rectangle {
        width: 3
        height: 1
    }

    Label {
        anchors.centerIn: parent
        text: root.valueText
    }
}
