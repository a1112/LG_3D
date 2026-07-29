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
            style: root.style
            alarmInfo: root.alarmInfo
        }

        DataShowRootLayout{
            surfaceData: root.surfaceData
            modelStore: root.modelStore
            controller: root.areaController
            primaryController: root.controller
            style: root.style
            adaptiveMetrics: root.adaptiveMetrics
            apiClient: root.apiClient
        // <----------
        // SplitView.fillWidth: true
        // SplitView.fillHeight:true
        }

        ShowViewListView{
            visible: root.controller.viewRendererListView
            implicitHeight: root.adaptiveMetrics.scaleMetric(100, 80, 130)
            SplitView.fillWidth: true
        }

        MaxMinValueShow{
            id:showViewListView
            visible: root.controller.viewRendererMaxMinValue
            implicitHeight: root.adaptiveMetrics.scaleMetric(40, 34, 54)
            SplitView.fillWidth: true
        }

    }
    DataShowItemFoot{
        Layout.fillWidth: true
    }
}
