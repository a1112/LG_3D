import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    anchors.centerIn: parent
    width: adaptive.boundedWidth(500, 380, 620)
    height: adaptive.boundedHeight(160, 150, 220)
    modal: true
    property alias ip_input_text: ip.text

    standardButtons: Dialog.Apply | Dialog.Ok

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        Label {
            text: qsTr("连接设置")
            font.pixelSize: adaptive.fontMetric(22, 18, 28)
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        TextFieldItem {
            id: ip
            title: qsTr("IP 地址")
            text: coreSetting.server_ip
            Layout.fillWidth: true
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Flow {
                anchors.fill: parent

                ShowItemDelegate { text: "127.0.0.1" }
                ShowItemDelegate { text: "10.9.41.112" }
                ShowItemDelegate { text: "192.168.99.100" }
            }
        }
    }

    onAccepted: coreSetting.server_ip = ip.text
}
