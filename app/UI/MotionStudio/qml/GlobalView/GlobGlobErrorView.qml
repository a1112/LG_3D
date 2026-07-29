import QtQuick
// 全局报警
Item {
    id: root

    required property var adaptiveMetrics
    required property var style
    required property var modelStore

    GlobalErrorView{
        anchors.centerIn: parent
        adaptiveMetrics: root.adaptiveMetrics
        style: root.style
        modelStore: root.modelStore
    }
    anchors.centerIn: parent
    scale: 3
}
