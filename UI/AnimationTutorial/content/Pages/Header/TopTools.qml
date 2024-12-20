import QtQuick
import QtQuick.Controls.Material
RowBase{
    y: -5
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "缺陷"
        font.bold: true
        height: root.height
        font.pixelSize: 15
        onClicked:{

        }
    }
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "诊断"
        font.bold: true
        height: root.height
        font.pixelSize: 15
        onClicked:{
            globalAlarmView.popup()
        }
    }
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "报表"
        font.bold: true
        height: root.height
        font.pixelSize: 15
        onClicked: {
           exportView.popup()
        }
    }


}
