pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Window
import QtQuick.Controls
import "PopupView"
import "fonts"
ApplicationWindow {
    id: appBase

    x:50
    y:50
    color: "#0B1117"
    flags: Qt.Window | Qt.FramelessWindowHint
    property PopManagement popManage
    property var apiClient
    property var adaptiveMetrics
    property var appStyle
    property var settingsStore
    property var appInfo
    property var downloadClient
    property var authManager
    property var graphsManager
    property var deviceCurveManager
    property var modelStore
    property var clipboardService
    property var toolService
    property var globalContext
    property var dialogManager

    Loader{
        anchors.fill:parent
        asynchronous:true
        sourceComponent:
        PopManagement{
            anchors.fill:parent
            apiClient: appBase.apiClient
            adaptiveMetrics: appBase.adaptiveMetrics
            appStyle: appBase.appStyle
            settingsStore: appBase.settingsStore
            appInfo: appBase.appInfo
            downloadClient: appBase.downloadClient
            authManager: appBase.authManager
            graphsManager: appBase.graphsManager
            deviceCurveManager: appBase.deviceCurveManager
            modelStore: appBase.modelStore
            clipboardService: appBase.clipboardService
            toolService: appBase.toolService
            globalContext: appBase.globalContext
            dialogManager: appBase.dialogManager
        }
        onLoaded: appBase.popManage = item
    }
    property LoadFont fonts :LoadFont{}
}
