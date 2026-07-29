pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "HardwareMonitorFormat.js" as Format

Rectangle {
    id: root

    required property var style
    required property var model
    required property int index

    color: index % 2 ? style.panelAlternateColor : "transparent"
    radius: 3

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 7
        anchors.rightMargin: 7

        MonitorStatusDot {
            style: root.style
            active: root.model.isUp
        }

        ColumnLayout {
            spacing: 0
            Layout.fillWidth: true

            Label {
                text: root.model.adapterName
                color: root.style.titleColor
                font.bold: true
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            Label {
                text: (root.model.ipv4 || "-") + "  "
                      + root.model.speedMbps + " Mbps"
                color: root.style.secondaryTextColor
                font.pixelSize: 11
            }
        }

        Label {
            text: "↓" + Format.formatRate(root.model.rxBytesPerSecond)
                  + "  ↑" + Format.formatRate(root.model.txBytesPerSecond)
            color: root.style.labelColor
        }
    }
}
