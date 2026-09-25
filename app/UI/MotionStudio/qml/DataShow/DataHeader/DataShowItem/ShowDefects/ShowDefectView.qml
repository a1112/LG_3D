import QtQuick.Controls
import QtQuick
import QtQuick.Layouts
ColumnLayout {
    id: root

    required property var surfaceData
    required property var controller
    required property var areaController
    required property var style
    required property var apiClient
    required property var globalContext

    anchors.fill:parent
    DefectShowHead{
        controller: root.controller
        defectClassController: root.globalContext.defectClassProperty
    }
    Item{
        Layout.fillWidth : true
        Layout.fillHeight : true
        Label{
            visible : false  // 不再显示"无缺陷报警"文字
            font.bold : true
            anchors.centerIn : parent
            text:qsTr("无缺陷报警！")
            font.pointSize : 28
            color : "green"
        }

        ShowDefectList{
            anchors.fill:parent
            model: root.controller.defectModel
            controller: root.controller
            areaController: root.areaController
            surfaceData: root.surfaceData
            style: root.style
            apiClient: root.apiClient
            defectClassController: root.globalContext.defectClassProperty
        }
    }
}
