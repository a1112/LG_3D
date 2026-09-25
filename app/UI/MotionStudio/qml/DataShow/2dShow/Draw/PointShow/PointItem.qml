import QtQuick

Item {
    id: root

    required property var dataShowCore
    required property var pointProjector
    required property real p_x
    required property real p_y
    required property real z_mm
    required property string type

    readonly property point labelPoint:
        root.pointProjector.findPoint(root.p_x, root.p_y, root.type)

    PointItemPointShow {
        dataShowCore: root.dataShowCore
        pointX: root.p_x
        pointY: root.p_y
    }

    PointItemLabelShow {
        dataShowCore: root.dataShowCore
        labelPoint: root.labelPoint
        zMm: root.z_mm
    }
}
