import QtQuick

Item {
    id: root

    required property var dataShowCore
    required property var style

    visible: root.dataShowCore.controls.surveyCanView
    anchors.fill: parent

    DrawSelectItem {
        dataShowCore: root.dataShowCore
        style: root.style
    }
}
