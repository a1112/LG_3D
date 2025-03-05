import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Dialog {
    anchors.centerIn: parent
    width: 500
    height: 200
    modal: true
    property alias ip_input_text: ip.text

    standardButtons: Dialog.Apply|Dialog.Ok
    ColumnLayout {
        anchors.fill: parent
        Label {
            text: "连接设置"
            font.pixelSize: 22
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }
        RowLayout{
        TextFieldItem {
            id:ip
            title: "Ip 地址"
            text: coreSetting.server_ip
        }

        TextFieldItem {
            width: 100
            id: port_id
            title: "端口号"
            text: coreSetting.server_port
        }
        }
        Item{
            Layout.fillWidth: true
            Layout.fillHeight: true
            Flow{
                anchors.fill: parent
                ShowItemDelegate{
                    text:"127.0.0.1"
                }
                ShowItemDelegate{
                    text:"192.168.99.100"
                }
            }
        }
    }

        onAccepted: {
            coreSetting.server_ip = ip.text
            coreSetting.server_port = port_id.text
        }

}
