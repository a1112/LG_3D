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

    visible: model.cap2D
    color: style.panelAlternateColor
    border.color: model.camera2DOk
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
                active: root.model.camera2DOk
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
                text: root.model.camera2DConnected
                      ? (root.model.state2D === "waiting_trigger"
                         ? "等待触发" : "采集中")
                      : "离线"
                color: root.model.camera2DOk
                       ? root.style.statusSuccessColor
                       : root.style.statusErrorColor
                font.bold: true
            }
        }

        Label {
            text: "最近帧: "
                  + (root.model.hasFrame2D
                     ? Format.formatAge(root.model.lastFrameAge2D) : "-")
                  + "    分辨率: "
                  + (root.model.width2D > 0
                     ? root.model.width2D + " × " + root.model.height2D : "-")
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
                              root.model.temperature2DAvailable,
                              root.model.temperature2D,
                              root.model.temperature2DStale)
                    color: Format.temperatureColor(
                               root.style,
                               root.model.temperature2DAvailable,
                               root.model.temperature2D,
                               root.model.temperature2DStale)
                    font.pixelSize: 19
                    font.bold: true
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 12
            rowSpacing: 2

            Label {
                text: "帧号 " + root.model.frameId2D
                color: root.style.labelColor
            }
            Label {
                text: "空帧 " + root.model.emptyFrames2D
                color: root.style.labelColor
            }
            Label {
                text: "错误 " + root.model.frameErrors2D
                      + " / 丢弃 " + root.model.droppedFrames2D
                color: root.style.labelColor
            }
            Label {
                text: "队列 " + root.model.queueSize2D
                      + " / 重连 " + root.model.connectAttempts2D
                color: root.style.labelColor
            }
            Label {
                text: "曝光 " + (root.model.exposureTime2D === null
                                ? "-" : root.model.exposureTime2D)
                color: root.style.labelColor
            }
            Label {
                text: "增益 " + (root.model.gain2D === null
                                ? "-" : root.model.gain2D)
                color: root.style.labelColor
            }
        }

        Label {
            text: root.model.error2D
                  || Format.temperatureAvailabilityText(
                      root.model.temperature2DError)
                  || "运行正常"
            color: root.model.error2D
                   ? root.style.statusErrorColor : root.style.labelColor
            Layout.fillWidth: true
            elide: Text.ElideMiddle
        }

        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }

            Button {
                text: "重连 2D"
                enabled: !root.model.busy
                onClicked: root.reconnectRequested(root.index)
            }
        }
    }
}
