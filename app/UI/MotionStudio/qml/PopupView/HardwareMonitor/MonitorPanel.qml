import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    required property var style
    property string panelTitle: ""
    property string panelCaption: ""
    default property alias content: panelBody.data

    color: style.panelElevatedColor
    border.color: style.headerBorderColor
    border.width: 1
    radius: style.controlRadius

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 9
        spacing: 6

        RowLayout {
            Layout.fillWidth: true

            Label {
                text: root.panelTitle
                color: root.style.titleColor
                font.bold: true
                font.pixelSize: 15
            }

            Label {
                text: root.panelCaption
                color: root.style.secondaryTextColor
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
        }

        Item {
            id: panelBody
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
