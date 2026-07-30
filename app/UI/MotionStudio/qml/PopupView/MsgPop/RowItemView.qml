import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ItemDelegate {
    id: root

    required property string itemKey
    required property string itemValue
    required property var style

    width: 150
    height: 25

    RowLayout {
        anchors.fill: parent
        spacing: 6

        Label {
            text: root.itemKey + ":"
            color: root.style.labelColor
            elide: Text.ElideRight
        }

        Label {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: root.itemValue
            color: root.style.titleColor
            font.pixelSize: 14
            font.bold: true
            elide: Text.ElideRight
            background: Rectangle {
                radius: 3
                color: root.style.panelBackgroundColor
                border.width: 1
                border.color: root.style.headerBorderColor
            }
        }
    }
}
