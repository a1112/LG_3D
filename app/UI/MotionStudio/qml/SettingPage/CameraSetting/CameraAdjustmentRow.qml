pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    required property var style
    required property var model
    required property int index

    signal saveRequested(int rowIndex, real exposureTime, real gain)
    signal reconnectRequested(int rowIndex)

    Layout.fillWidth: true
    implicitHeight: rowLayout.implicitHeight + 18
    color: "transparent"
    border.color: style.headerBorderColor
    border.width: 1
    radius: style.controlRadius

    readonly property color statusColor:
        model.connected && model.ok
        ? style.statusSuccessColor
        : model.connected
          ? style.statusWarningColor : style.statusErrorColor

    RowLayout {
        id: rowLayout
        anchors.fill: parent
        anchors.margins: 9
        spacing: 12

        Rectangle {
            Layout.preferredWidth: 10
            Layout.preferredHeight: 38
            radius: 5
            color: root.statusColor
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.minimumWidth: 220
            spacing: 4

            RowLayout {
                spacing: 8
                Layout.fillWidth: true

                Label {
                    text: root.model.key
                    color: root.style.titleColor
                    font.pixelSize: 15
                    font.bold: true
                }

                Label {
                    text: root.model.connected ? qsTr("在线") : qsTr("离线")
                    color: root.statusColor
                    font.pixelSize: 13
                }
            }

            Label {
                text: (root.model.name || "-")
                      + "  SN: " + (root.model.sn || "-")
                color: root.style.labelColor
                font.pixelSize: 12
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            Label {
                text: qsTr("最近帧") + ": "
                      + root.formatAge(root.model.lastFrameAge)
                      + "    3D: "
                      + root.formatAge(root.model.lastFrameAge3D)
                      + "    " + qsTr("参数源") + ": "
                      + (root.model.source || "-")
                color: root.style.secondaryTextColor
                font.pixelSize: 12
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            Label {
                text: root.model.message || root.model.lastError3D
                      || root.model.serviceUrl || root.model.paramFile
                      || root.model.yamlConfig
                color: root.style.secondaryTextColor
                font.pixelSize: 11
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
        }

        ColumnLayout {
            spacing: 6
            Layout.preferredWidth: 150

            Label {
                text: qsTr("曝光时间")
                color: root.style.labelColor
                font.pixelSize: 12
            }

            SpinBox {
                id: exposureBox
                from: 1
                to: 1000000
                value: root.model.exposureTime
                editable: true
                enabled: root.model.writable && !root.model.busy
                Layout.fillWidth: true
            }
        }

        ColumnLayout {
            spacing: 6
            Layout.preferredWidth: 120

            Label {
                text: qsTr("增益")
                color: root.style.labelColor
                font.pixelSize: 12
            }

            SpinBox {
                id: gainBox
                from: 0
                to: 1000
                value: root.model.gain
                editable: true
                enabled: root.model.writable && !root.model.busy
                Layout.fillWidth: true
            }
        }

        ColumnLayout {
            spacing: 6
            Layout.preferredWidth: 88

            Button {
                text: root.model.busy ? qsTr("处理中") : qsTr("保存")
                enabled: root.model.writable && !root.model.busy
                Layout.fillWidth: true
                onClicked: root.saveRequested(
                               root.index, exposureBox.value, gainBox.value)
            }

            Button {
                text: qsTr("重连")
                enabled: !root.model.busy
                Layout.fillWidth: true
                onClicked: root.reconnectRequested(root.index)
            }
        }
    }

    function formatAge(value) {
        let age = Number(value)
        return isFinite(age) ? age.toFixed(1) + " s" : "-"
    }
}
