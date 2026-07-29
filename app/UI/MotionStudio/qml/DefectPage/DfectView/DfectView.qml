import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../"

RowLayout {
    id: root

    required property var defectController
    required property var style
    required property var modelStore
    required property var settings
    required property var appController
    required property var apiClient
    required property var coreController

    CardBaseView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        defectController: root.defectController
        style: root.style
        modelStore: root.modelStore
        settings: root.settings
        appController: root.appController
        apiClient: root.apiClient
        coreController: root.coreController
    }
}
