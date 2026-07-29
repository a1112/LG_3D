import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Head"
import "HistoryView"
import "Core"
Item {
    id: root

    required property var adaptiveMetrics
    required property var style
    required property var modelStore
    required property var settings
    required property var appController
    required property var leftController
    required property var apiClient
    required property var popupManager
    required property var globalContext
    required property var coreController
    required property var toolService
    required property var authManager

    property DefectViewCore defectViewCore: DefectViewCore {
        appController: root.appController
        apiClient: root.apiClient
        modelStore: root.modelStore
        globalContext: root.globalContext
        toolService: root.toolService
    }

    ColumnLayout{
        anchors.fill: parent
            SplitView{
                Layout.fillWidth: true
                Layout.fillHeight: true
                LeftDataView{   // 主要界面
                    defectController: root.defectViewCore
                    style: root.style
                    modelStore: root.modelStore
                    settings: root.settings
                    appController: root.appController
                    apiClient: root.apiClient
                    coreController: root.coreController
                }
                RightViewList{
                    adaptiveMetrics: root.adaptiveMetrics
                    defectController: root.defectViewCore
                    style: root.style
                    leftController: root.leftController
                    apiClient: root.apiClient
                    modelController: root.modelStore
                    popupManager: root.popupManager
                    coreController: root.coreController
                    authManager: root.authManager
                }
            }


    }
}
