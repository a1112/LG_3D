import QtQuick.Controls
import QtQuick.Layouts
import "Pages/LeftPage"
import "DataShow"
/*
    图像显示主界面


*/
SplitView{
    id: root

    required property var adaptiveMetrics
    required property var style
    required property var model
    required property var settings
    required property var viewControl
    required property var alarmInfo
    required property var apiClient
    required property var popupManager
    required property var leftController
    required property var coreController
    required property var toolService
    required property var imageCacheService
    required property var authManager
    required property var globalContext

    Layout.fillWidth: true
    Layout.fillHeight: true
    LeftPageView{  // 左侧列表
        id:left
        adaptiveMetrics: root.adaptiveMetrics
        style: root.style
        modelStore: root.model
        popupManager: root.popupManager
        leftController: root.leftController
        apiClient: root.apiClient
        alarmInfo: root.alarmInfo
        coreController: root.coreController
        toolService: root.toolService
        authManager: root.authManager
        globalContext: root.globalContext
        SplitView.fillHeight: true
        SplitView.preferredWidth: root.style.leftWidth
        SplitView.minimumWidth: root.style.leftMinimumWidth
        SplitView.maximumWidth: root.style.leftMaximumWidth
    }
    DataShowLayout{    // 数据显示
        Layout.fillWidth: true
        Layout.fillHeight: true
        adaptiveMetrics: root.adaptiveMetrics
        style: root.style
        model: root.model
        settings: root.settings
        viewControl: root.viewControl
        alarmInfo: root.alarmInfo
        apiClient: root.apiClient
        globalContext: root.globalContext
        toolService: root.toolService
        imageCacheService: root.imageCacheService
    }
}
