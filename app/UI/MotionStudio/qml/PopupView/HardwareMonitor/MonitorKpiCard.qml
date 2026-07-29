import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    required property var style
    property string title: ""
    property string value: ""
    property string detail: ""
    property color accent: style.statusSuccessColor

    Layout.fillWidth: true
    Layout.preferredHeight: 72
    color: style.panelAlternateColor
    border.color: accent
    border.width: 1
    radius: style.controlRadius

    RowLayout {
        anchors.fill: parent
        anchors.margins: 10

        Rectangle {
            Layout.preferredWidth: 4
            Layout.fillHeight: true
            color: root.accent
            radius: 2
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 1

            Label {
                text: root.title
                color: root.style.secondaryTextColor
            }

            Label {
                text: root.value
                color: root.accent
                font.pixelSize: 20
                font.bold: true
            }

            Label {
                text: root.detail
                color: root.style.secondaryTextColor
                opacity: 0.8
                font.pixelSize: 11
            }
        }
    }
}
