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

    signal actionRequested(int rowIndex, string action)

    color: style.panelAlternateColor
    border.color: model.isUp
                  ? style.statusSuccessColor : style.statusInactiveColor
    radius: style.controlRadius

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 5

        RowLayout {
            Layout.fillWidth: true

            MonitorStatusDot {
                style: root.style
                active: root.model.isUp
            }

            Label {
                text: root.model.adapterName
                color: root.style.titleColor
                font.bold: true
                font.pixelSize: 15
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            Label {
                text: root.model.isUp ? "在线" : "离线"
                color: root.model.isUp
                       ? root.style.statusSuccessColor
                       : root.style.statusInactiveColor
                font.bold: true
            }
        }

        Label {
            text: "IPv4: " + (root.model.ipv4 || "-")
            color: root.style.labelColor
            Layout.fillWidth: true
            elide: Text.ElideMiddle
        }

        Label {
            text: "MAC: " + (root.model.mac || "-")
                  + "    链路: "
                  + (root.model.speedMbps > 0
                     ? root.model.speedMbps + " Mbps" : "-")
                  + "    MTU: " + root.model.mtu
            color: root.style.secondaryTextColor
        }

        Label {
            text: "↓ " + Format.formatRate(root.model.rxBytesPerSecond)
                  + "    ↑ " + Format.formatRate(root.model.txBytesPerSecond)
                  + "    错误 " + root.model.errors
                  + " / 丢包 " + root.model.drops
            color: root.style.labelColor
        }

        Label {
            text: "累计接收 " + Format.formatBytes(root.model.bytesReceived)
                  + " / 发送 " + Format.formatBytes(root.model.bytesSent)
            color: root.style.secondaryTextColor
        }

        RowLayout {
            Layout.fillWidth: true

            Label {
                text: root.model.canControl
                      ? "" : Format.networkControlReason(
                          root.model.controlReason)
                color: root.style.statusWarningColor
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            Button {
                text: root.model.isUp ? "禁用" : "启用"
                enabled: root.model.canControl && !root.model.busy
                onClicked: root.actionRequested(
                               root.index,
                               root.model.isUp ? "disable" : "enable")
            }

            Button {
                text: "重启"
                visible: root.model.isUp
                enabled: root.model.canControl && !root.model.busy
                onClicked: root.actionRequested(root.index, "restart")
            }
        }
    }
}
