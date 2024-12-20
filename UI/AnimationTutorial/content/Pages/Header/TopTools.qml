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
            popManage.popupDefectClassPop()
        }
    }
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "诊断"
        font.bold: true
        height: root.height
        font.pixelSize: 15
        onClicked:{
            popManage.popupGlobalAlarmView()
        }
    }
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "报表"
        font.bold: true
        height: root.height
        font.pixelSize: 15
        onClicked: {
           popManage.popupExportView()
        }
    }


}
