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
    required property var globalContext
    required property var settings
    required property var view3DController

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
        globalContext: root.globalContext
        settings: root.settings
        view3DController: root.view3DController
        adaptiveMetrics: root.adaptiveMetrics
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
