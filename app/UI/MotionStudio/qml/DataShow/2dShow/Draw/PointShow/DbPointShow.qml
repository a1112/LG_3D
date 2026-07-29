pragma ComponentBehavior: Bound

import QtQuick

Item {
    id: root

    required property var dataShowCore
    required property var innerEllipse

    anchors.fill: parent

    readonly property real centreX: root.innerEllipse[0]
        ? Number(root.innerEllipse[0][0]) || 0 : 0
    readonly property real centreY: root.innerEllipse[0]
        ? Number(root.innerEllipse[0][1]) || 0 : 0
    readonly property real ellipseWidth: root.innerEllipse[1]
        ? Math.min(Number(root.innerEllipse[1][0]) || 0,
                   Number(root.innerEllipse[1][1]) || 0) : 0

    function findPoint(px, py, pointType) {
        const cx = root.centreX
        const cy = root.centreY
        const dx = px - cx
        const dy = py - cy
        const distance = Math.sqrt(dx ** 2 + dy ** 2)
        let radius

        if (pointType === "max_inner") {
            radius = Math.max(root.ellipseWidth / 2 - 100, 0)
        } else if (pointType === "min_inner") {
            radius = Math.max(root.ellipseWidth / 2 - 200, 0)
        } else if (pointType === "max_outer") {
            radius = Math.max(distance - 100, 0)
        } else if (pointType === "min_outer") {
            radius = Math.max(distance - 200, 0)
        } else {
            return Qt.point(px, py)
        }

        if (distance === 0) {
            return Qt.point(px, py)
        }

        return Qt.point(cx + dx / distance * radius,
                        cy + dy / distance * radius)
    }

    Repeater {
        model: root.dataShowCore.pointDbData
        delegate: PointItem {
            dataShowCore: root.dataShowCore
            pointProjector: root
        }
    }
}
