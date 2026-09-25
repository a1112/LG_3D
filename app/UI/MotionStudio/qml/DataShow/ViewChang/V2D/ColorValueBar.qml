pragma ComponentBehavior: Bound

import QtQuick

Row {
    id: root

    x: parent.width + 10
    spacing: 5

    property real maxValue: 127
    property real minValue: -127
    readonly property real itemHeight: height / listView.count
    readonly property bool hoved: hoverHandler.hovered
    property color labelColor: "#FFF"

    function getHovText(posY) {
        return (((root.height - posY) / root.height)
                * (root.maxValue - root.minValue) + root.minValue).toFixed(1)
    }

    function getValueByModelIndex(modelIndex) {
        let count = listView.count
        return "" + ((count - modelIndex) / count
                     * (root.maxValue - root.minValue) + root.minValue).toFixed(0)
    }

    GetRec {
        width: 20
        height: parent.height

        HoverHandler {
            id: hoverHandler
        }

        HovedLabel {
            y: hoverHandler.point.position.y - height / 2
            anchors.right: parent.left
            visible: hoverHandler.hovered
            text: root.getHovText(hoverHandler.point.position.y)
            background: Rectangle {
                color: "black"
            }
        }
    }

    ListView {
        id: listView

        height: parent.height
        width: 30
        model: 10
        delegate: ValueItemItem {
            required property int index

            rowHeight: root.itemHeight
            valueText: root.getValueByModelIndex(index)
        }
    }
}
