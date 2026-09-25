import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "DefectPage"

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

    Layout.fillWidth: true
    Layout.fillHeight: true
    DefectShowLayout {
        anchors.fill: parent
        adaptiveMetrics: root.adaptiveMetrics
        style: root.style
        modelStore: root.modelStore
        settings: root.settings
        appController: root.appController
        leftController: root.leftController
        apiClient: root.apiClient
        popupManager: root.popupManager
        globalContext: root.globalContext
        coreController: root.coreController
        toolService: root.toolService
        authManager: root.authManager
    }
}
