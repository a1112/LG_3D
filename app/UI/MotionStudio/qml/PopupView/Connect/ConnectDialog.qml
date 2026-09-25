pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: root
    required property var adaptiveMetrics
    required property var settings
    required property var style

    anchors.centerIn: parent
    width: root.adaptiveMetrics.boundedWidth(500, 380, 620)
    height: root.adaptiveMetrics.boundedHeight(210, 190, 270)
    modal: true
    readonly property string normalizedHost: ip.text.trim()
    readonly property bool acceptableHost: root.isValidHost(root.normalizedHost)
    readonly property var presetHosts: ["127.0.0.1", "localhost", "10.9.41.112"]

    standardButtons: Dialog.Cancel | Dialog.Ok

    function isValidHost(host) {
        return host.length > 0
                && host.length <= 253
                && host.indexOf("://") < 0
                && host.indexOf("/") < 0
                && host.indexOf("\\") < 0
                && host.indexOf(":") < 0
                && !/\s/.test(host)
                && /^[A-Za-z0-9.-]+$/.test(host)
                && host.charAt(0) !== "."
                && host.charAt(host.length - 1) !== "."
    }

    onOpened: {
        ip.text = root.settings.server_ip
        ip.forceInputFocus()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        Label {
            text: qsTr("连接设置")
            font.pixelSize: root.adaptiveMetrics.fontMetric(22, 18, 28)
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        TextFieldItem {
            id: ip
            title: qsTr("IP 地址")
            text: root.settings.server_ip
            Layout.fillWidth: true
        }

        Label {
            visible: !root.acceptableHost && ip.text.length > 0
            text: qsTr("请输入不含协议和端口的主机名或 IP 地址")
            color: root.style.statusErrorColor
            Layout.fillWidth: true
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Flow {
                anchors.fill: parent

                Repeater {
                    model: root.presetHosts
                    ItemDelegate {
                        required property string modelData
                        text: modelData
                        onClicked: ip.text = modelData
                    }
                }
            }
        }
    }

    onAccepted: {
        if (root.acceptableHost) {
            root.settings.server_ip = root.normalizedHost
        } else {
            Qt.callLater(root.open)
        }
    }
}
