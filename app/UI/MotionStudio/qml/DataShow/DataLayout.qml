import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "Foot"
import "MaxMinValue"
import "DataHeader"
ColumnLayout{
    id: root

    required property var surfaceData
    required property var modelStore
    required property var controller
    required property var areaController
    required property var style
    required property var settings
    required property var adaptiveMetrics
    required property var alarmInfo
    required property var apiClient
    required property var globalContext
    required property var view3DController

    anchors.fill:parent
    SplitView{
        Layout.fillWidth: true
        Layout.fillHeight: true
        orientation: Qt.Vertical

        DataHeaderView{
            SplitView.fillWidth: true
            SplitView.preferredHeight: root.settings.dataHeaderHeight
            surfaceData: root.surfaceData
            controller: root.controller
            areaController: root.areaController
            style: root.style
            alarmInfo: root.alarmInfo
            apiClient: root.apiClient
            globalContext: root.globalContext
        }

        DataShowRootLayout{
            surfaceData: root.surfaceData
            modelStore: root.modelStore
            controller: root.areaController
            primaryController: root.controller
            style: root.style
            adaptiveMetrics: root.adaptiveMetrics
            apiClient: root.apiClient
            globalContext: root.globalContext
            view3DController: root.view3DController
            settings: root.settings
        // <----------
        // SplitView.fillWidth: true
        // SplitView.fillHeight:true
        }

        ShowViewListView{
            visible: root.controller.viewRendererListView
            implicitHeight: root.adaptiveMetrics.scaleMetric(100, 80, 130)
            SplitView.fillWidth: true
            surfaceData: root.surfaceData
            controller: root.controller
            style: root.style
        }

        MaxMinValueShow{
            id:showViewListView
            visible: root.controller.viewRendererMaxMinValue
            implicitHeight: root.adaptiveMetrics.scaleMetric(40, 34, 54)
            SplitView.fillWidth: true
        }

    }
    FootToolBar {
        Layout.fillWidth: true
        surfaceData: root.surfaceData
        controller: root.controller
        style: root.style
    }
}
