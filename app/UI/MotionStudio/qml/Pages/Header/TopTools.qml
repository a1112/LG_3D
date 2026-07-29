import QtQuick
import QtQuick.Controls.Material
RowBase{
    id: root

    required property var adaptiveMetrics
    required property var popupManager

    y: root.adaptiveMetrics.headerOffset
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "缺陷"
        font.bold: true
        height: root.height
        onClicked:{
            root.popupManager.popupDefectClassPop()
        }
    }
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "诊断"
        font.bold: true
        height: root.height
        onClicked:{
            root.popupManager.popupGlobalAlarmView()
        }
    }
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "报表"
        font.bold: true
        height: root.height
        onClicked: {
           root.popupManager.popupExportView()
        }
    }
    ItemDelegate{
        anchors.verticalCenter: parent.verticalCenter
        text: "设备"
        font.bold: true
        height: root.height
        onClicked: {
            root.popupManager.popupHardwareMonitorView()
        }
    }


}
