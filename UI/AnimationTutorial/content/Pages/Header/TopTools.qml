import QtQuick
import QtQuick.Controls.Material
RowBase{
    y: -5
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "缺陷列表"
        font.bold: true
        height: root.height
        font.pixelSize: 15
    }
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "设备诊断"
        font.bold: true
        height: root.height
        font.pixelSize: 15
        onClicked:{
            globalAlarmView.popup()
        }
    }
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "报表打印"
        font.bold: true
        height: root.height
        font.pixelSize: 15
        onClicked: {
           exportView.popup()
        }
    }
}
