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

    signal reconnectRequested(int rowIndex)
    signal resetRequested(int rowIndex)

    visible: model.cap3D
    color: style.panelAlternateColor
    border.color: model.camera3DOk
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
                active: root.model.camera3DOk
            }

            Label {
                text: root.model.cameraKey + "  " + root.model.cameraName
                color: root.style.titleColor
                font.bold: true
                font.pixelSize: 15
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            Label {
                text: root.model.camera3DAcquiring
                      ? "采集中"
                      : root.model.camera3DConnected ? "已连接" : "离线"
                color: root.model.camera3DOk
                       ? root.style.statusSuccessColor
                       : root.style.statusErrorColor
                font.bold: true
            }
        }

        Label {
            text: "SN: " + (root.model.sn || "-") + "    最近帧: "
                  + (root.model.hasFrame3D
                     ? Format.formatAge(root.model.lastFrameAge3D) : "-")
            color: root.style.secondaryTextColor
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            color: root.style.panelElevatedColor
            radius: 4

            RowLayout {
                anchors.fill: parent
                anchors.margins: 8

                Label {
                    text: "设备温度"
                    color: root.style.labelColor
                    Layout.fillWidth: true
                }

                Label {
                    text: Format.formatTemperature(
                              root.model.temperature3DAvailable,
                              root.model.temperature3D,
                              root.model.temperature3DStale)
                    color: Format.temperatureColor(
                               root.style,
                               root.model.temperature3DAvailable,
                               root.model.temperature3D,
                               root.model.temperature3DStale)
                    font.pixelSize: 19
                    font.bold: true
                }
            }
        }

        Label {
            text: "启动失败: " + root.model.startFailures
                  + "    最后动作: " + (root.model.last3DAction || "-")
            color: root.style.secondaryTextColor
            Layout.fillWidth: true
            elide: Text.ElideRight
        }

        Label {
            text: root.model.error3D
                  || root.model.temperature3DError || "运行正常"
            color: root.model.error3D
                   ? root.style.statusErrorColor : root.style.labelColor
            Layout.fillWidth: true
            elide: Text.ElideMiddle
        }

        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }

            Button {
                text: "重连 3D"
                enabled: !root.model.busy
                onClicked: root.reconnectRequested(root.index)
            }

            Button {
                text: "复位 3D"
                enabled: !root.model.busy
                onClicked: root.resetRequested(root.index)
            }
        }
    }
}
