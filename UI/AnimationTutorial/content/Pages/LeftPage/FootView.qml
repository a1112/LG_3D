import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material
Item {
    Layout.fillWidth: true
    height: 25
    RowLayout {
        anchors.fill: parent
        Label{
            text: api.apiConfig.serverUrl
            baseUrl: api.apiConfig.serverUrl
            color: api.connectColor
        ItemDelegate{
            anchors.fill:parent
            onClicked: {
                connectDialog.open()
            }
        }
        }
        Label{
            text: "延时："
        }
        Label{
            text: api.delay
            color: api.connectColor
        }

        Label{
            visible:false
            text: "检测记录：" +coreModel.currentCoilListModel.count
        }
        Item{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
        Row{
        CheckDelegate{
            height: 25
            text: "保持最新"
            checked: coreModel.keepLatest
            onClicked: {
                coreModel.setKeepLatest(checked)
            }
        }
        }
    }
}

