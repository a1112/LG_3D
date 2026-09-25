import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "DfectView"
import "Head"
import "../Base"
ColumnLayout {
    id: root

    required property var defectController
    required property var style
    required property var modelStore
    required property var settings
    required property var appController
    required property var apiClient
    required property var coreController
    required property var globalContext

    SplitView.fillHeight: true
    SplitView.fillWidth: true

    HeadToolBox {
        Layout.fillWidth: true
        defectController: root.defectController
        style: root.style
        apiClient: root.apiClient
        coreController: root.coreController
    }

    DfectView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        defectController: root.defectController
        style: root.style
        modelStore: root.modelStore
        settings: root.settings
        appController: root.appController
        apiClient: root.apiClient
        coreController: root.coreController
        globalContext: root.globalContext
    }
}

