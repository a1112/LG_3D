import QtQuick
import QtQuick.Controls

Label {
    id: root

    required property var dataShowCore
    required property point labelPoint
    required property real zMm

    x: root.dataShowCore.toPx(root.labelPoint.x) - root.width / 2
    y: root.dataShowCore.toPx(root.labelPoint.y) - root.height / 2
    text: root.zMm.toFixed(0)
    color: root.zMm > 50 ? "red" : "yellow"
}
