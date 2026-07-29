import QtQuick 2.15
import QtQuick.Controls 2.15
// 十字架
Item {
    id: root

    required property var dataShowCore
    required property var surfaceData
    required property var style

    anchors.fill: parent
    visible: true
    property real crossY: 0
    property real crossX: 0
    readonly property real hoveredZ: Number(root.dataShowCore.hoverdZmm)
    readonly property bool zOutOfRange:
        isFinite(root.hoveredZ)
        && (root.hoveredZ < root.surfaceData.tower_warning_threshold_down
            || root.hoveredZ > root.surfaceData.tower_warning_threshold_up)

    DashHLine{
        visible: root.dataShowCore.imageShowHovered
        lineWidth:1
        width: 20
        x: root.crossX - 10
        y: root.crossY

    }
    Label{
    color: root.style.statusErrorColor
    text: root.dataShowCore.hoverdYmm + " mm"
        anchors.left: parent.left
    z:-height
    y: root.crossY
    background: Rectangle{
        color: root.style.headerBackgroundColor
        radius: 5
    }
    }
    DashVLine{
        lineWidth:1
        height: 20
        z:-height
        x: root.crossX
        y: root.crossY - 10
    }
    Label{
        anchors.bottom: parent.bottom
        color: root.style.statusErrorColor
        text: root.dataShowCore.hoverdXmm + " mm"
        x: root.crossX
        background: Rectangle{
            color: root.style.headerBackgroundColor
            radius: 5
        }
    }

    Label{
        color: root.zOutOfRange ? root.style.statusErrorColor
                                : root.style.statusSuccessColor
        text: root.dataShowCore.hoverdZmm
        y: root.crossY - 30
        x: root.crossX - 30
        scale:1
        background: Rectangle{
            color: root.style.headerBackgroundColor
            radius: 5
        }
    }
}
