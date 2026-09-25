pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "HardwareMonitorFormat.js" as Format

Rectangle {
    id: root

    required property var style
    required property var model
    required property int index

    signal restartRequested(int rowIndex)

    color: style.panelAlternateColor
    border.color: model.online
                  ? style.statusSuccessColor : style.statusErrorColor
    radius: style.controlRadius

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 5

        RowLayout {
            Layout.fillWidth: true

            MonitorStatusDot {
                style: root.style
                active: root.model.online
            }

            Label {
                text: root.model.serviceName
                color: root.style.titleColor
                font.bold: true
                font.pixelSize: 15
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            Rectangle {
                implicitWidth: categoryText.width + 12
                implicitHeight: 23
                color: root.style.panelElevatedColor
                radius: 3

                Label {
                    id: categoryText
                    anchors.centerIn: parent
                    text: root.model.category
                    color: root.style.labelColor
                    font.pixelSize: 11
                }
            }

            Label {
                text: root.model.online ? "运行中" : root.model.stateText
                color: root.model.online
                       ? root.style.statusSuccessColor
                       : root.style.statusErrorColor
                font.bold: true
            }
        }

        Label {
            text: root.model.hasPort
                  ? "端点 " + root.model.host + ":" + root.model.port
                  : "后台进程"
            color: root.style.labelColor
        }

        Label {
            text: "PID " + (root.model.hasPid ? root.model.pid : "-")
                  + "    " + (root.model.processName || "-")
            color: root.style.secondaryTextColor
        }

        Label {
            text: "运行 "
                  + (root.model.hasUptime
                     ? Format.formatDuration(root.model.uptimeSeconds) : "-")
                  + "    内存 "
                  + Format.formatBytes(root.model.memoryBytes)
            color: root.style.secondaryTextColor
        }

        RowLayout {
            Layout.fillWidth: true

            Label {
                text: root.model.message || root.model.commandLine || "-"
                color: root.model.online
                       ? root.style.labelColor : root.style.statusErrorColor
                Layout.fillWidth: true
                elide: Text.ElideMiddle
            }

            Button {
                visible: root.model.canRestart
                enabled: !root.model.busy
                text: root.model.busy ? "重启中" : "重启"
                Material.background: Material.Orange
                onClicked: root.restartRequested(root.index)
            }
        }
    }
}
