pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    required property var style

    Layout.fillWidth: true
    Layout.fillHeight: true

    property string title: qsTr("S端")
    property alias model: gridView.model

    ColumnLayout {
        anchors.fill: parent

        Label {
            Layout.alignment: Qt.AlignHCenter
            text: root.title
            color: root.style.titleColor
            font.bold: true
            font.pixelSize: 24
        }

        GridView {
            id: gridView

            Layout.fillWidth: true
            Layout.fillHeight: true
            cellWidth: gridView.width / 2 - 5
            cellHeight: 25
            model: ListModel {
                dynamicRoles: true
            }
            delegate: RowItemView {
                required property string key
                required property string value

                width: gridView.cellWidth
                itemKey: key
                itemValue: value
                style: root.style
            }
        }
    }
}
