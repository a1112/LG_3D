import QtQuick
import QtQuick.Controls.Material
RowBase{
    id: root
    y: adaptive.headerOffset
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "缺陷"
        font.bold: true
        height: root.height
        font.pixelSize: adaptive.fontMetric(15, 13, 18)
        onClicked:{
            popManage.popupDefectClassPop()
        }
    }
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "诊断"
        font.bold: true
        height: root.height
        font.pixelSize: adaptive.fontMetric(15, 13, 18)
        onClicked:{
            popManage.popupGlobalAlarmView()
        }
    }
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "报表"
        font.bold: true
        height: root.height
        font.pixelSize: adaptive.fontMetric(15, 13, 18)
        onClicked: {
           popManage.popupExportView()
        }
    }
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "设备"
        font.bold: true
        height: root.height
        font.pixelSize: adaptive.fontMetric(15, 13, 18)
        onClicked: {
            popManage.popupHardwareMonitorView()
        }
    }


}
