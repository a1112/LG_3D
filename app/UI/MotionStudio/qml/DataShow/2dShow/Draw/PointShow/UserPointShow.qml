pragma ComponentBehavior: Bound

import QtQuick

Item {
    id: root

    required property var dataShowCore
    required property var surfaceData
    required property var style
    required property var apiClient

    anchors.fill: parent

    Repeater {
        model: root.dataShowCore.pointUserData
        delegate: PointViewItem {
            dataShowCore: root.dataShowCore
            surfaceData: root.surfaceData
            style: root.style
            apiClient: root.apiClient
        }
    }
}
