import QtQuick

Rectangle {
    id: root

    required property var dataShowCore
    required property real pointX
    required property real pointY

    x: root.dataShowCore.toPx(root.pointX) - root.width / 2
    y: root.dataShowCore.toPx(root.pointY) - root.height / 2
    width: 4
    height: 4
    radius: root.width / 2
    color: "transparent"
    border.width: 2
    border.color: "red"
}
