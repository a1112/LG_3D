import QtQuick
import QtQuick.Controls

Rectangle {
    id: root

    required property var apiClient
    required property var surfaceData
    required property var dataShowCore
    required property var style
    required property real p_x
    required property real p_y

    property real zValue: 0

    function fetchZValue() {
        root.apiClient.get_zValueData(
                    root.surfaceData.key,
                    root.surfaceData.coilId,
                    root.p_x,
                    root.p_y,
                    result => {
                        root.zValue = Number(result) || 0
                    },
                    error => {
                        console.warn("get_zValueData failed:", error)
                    })
    }

    x: root.dataShowCore.toPx(root.p_x) - 4
    y: root.dataShowCore.toPx(root.p_y) - 4
    width: 8
    height: 8
    radius: 4
    color: "transparent"
    border.width: 2
    border.color: root.style.statusSuccessColor

    Label {
        anchors.right: parent.left
        anchors.top: parent.bottom
        anchors.horizontalCenterOffset: 15
        anchors.verticalCenterOffset: 15
        text: root.surfaceData.i_to_info(root.zValue)
        color: root.style.statusWarningColor
        background: Rectangle {
            color: root.style.infoOverlayColor
        }
    }

    Component.onCompleted: root.fetchZValue()
}
