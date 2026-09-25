pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "HardwareMonitorFormat.js" as Format

Rectangle {
    id: root

    required property var style
    required property var model

    color: style.panelAlternateColor
    border.color: model.healthy
                  ? style.statusSuccessColor : style.statusErrorColor
    radius: style.controlRadius

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 3

        RowLayout {
            Layout.fillWidth: true

            MonitorStatusDot {
                style: root.style
                active: root.model.healthy
            }

            Label {
                text: root.model.cameraKey + "  " + root.model.cameraName
                color: root.style.titleColor
                font.bold: true
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            Label {
                text: root.model.captureRunning ? "采集中" : "待采集"
                color: root.model.captureRunning
                       ? root.style.statusSuccessColor
                       : root.style.statusInactiveColor
            }
        }

        RowLayout {
            Layout.fillWidth: true

            Label {
                text: "3D " + (root.model.camera3DOk ? "正常" : "异常")
                      + "  " + Format.formatTemperature(
                          root.model.temperature3DAvailable,
                          root.model.temperature3D,
                          root.model.temperature3DStale)
                color: root.model.camera3DOk
                       ? root.style.statusSuccessColor
                       : root.style.statusWarningColor
                Layout.fillWidth: true
            }

            Label {
                text: "2D " + (root.model.camera2DOk ? "正常" : "异常")
                      + "  " + Format.formatTemperature(
                          root.model.temperature2DAvailable,
                          root.model.temperature2D,
                          root.model.temperature2DStale)
                color: root.model.camera2DOk
                       ? root.style.statusSuccessColor
                       : root.style.statusWarningColor
                Layout.fillWidth: true
            }
        }

        Label {
            text: root.model.error3D || root.model.error2D || "运行正常"
            color: root.model.error3D || root.model.error2D
                   ? root.style.statusErrorColor : root.style.secondaryTextColor
            Layout.fillWidth: true
            elide: Text.ElideMiddle
        }
    }
}
