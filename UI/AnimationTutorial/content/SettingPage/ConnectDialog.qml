import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Dialog {
    anchors.centerIn: parent
    width: 500
    height: 300
    modal: true
    standardButtons: Dialog.Apply|Dialog.Ok
    ColumnLayout {
        anchors.fill: parent
        Label {
            text: "连接设置"
            font.pixelSize: 22
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }
        TextFieldItem {
            id:ip
            title: "Ip 地址"
            text: coreSetting.server_ip
        }
        Item{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }

        onAccepted: {
            coreSetting.server_ip = ip.text
        }

}
