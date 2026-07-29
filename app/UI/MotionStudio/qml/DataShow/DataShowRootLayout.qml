import QtQuick
import QtQuick.Layouts

import "Header"

Item {
    id: root

    required property var surfaceData
    required property var modelStore
    required property var controller
    required property var primaryController
    required property var style
    required property var adaptiveMetrics
    required property var apiClient

    DataShowItemHead{
        id:dsh
        surfaceData: root.surfaceData
        controller: root.primaryController
        areaController: root.controller
        style: root.style
    }

    DataShowRootView{   // show
        Layout.fillWidth: true
        Layout.fillHeight: true
        id:dsr
        surface: root.surfaceData
        modelStore: root.modelStore
        controller: root.controller
        style: root.style
        apiClient: root.apiClient
    }

    ColumnLayout{
        anchors.fill:parent

        LayoutItemProxy{
            Layout.fillWidth: true
            target:dsh
            height: root.adaptiveMetrics.scaleMetric(27, 24, 36)
        }

        LayoutItemProxy{
            Layout.fillWidth: true
            Layout.fillHeight:true
            target:dsr
        }
    }

}
