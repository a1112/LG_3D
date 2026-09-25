pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
Rectangle {
    id: root
    required property var model
    required property var controller
    required property var defectClassController
    required property var style

    readonly property string defectName: root.model.configDefectName || root.model.defectName || ""
    readonly property color defectColor: root.defectClassController.getColorByName(root.defectName)
    visible: root.controller.defect_show(root.defectName)
    x: (Number(root.model.defectX) || 0) * root.controller.canvasScale
    y: (Number(root.model.defectY) || 0) * root.controller.canvasScale
    width: Math.max(0, Number(root.model.defectW) || 0) * root.controller.canvasScale
    height: Math.max(0, Number(root.model.defectH) || 0) * root.controller.canvasScale
    border.color: root.defectColor
    border.width: 2
    opacity: 0.8
    color: "transparent"
    Label {
        visible: root.defectClassController.defeftDrawShowLasbel
        color: Qt.lighter(root.defectColor)
        text: root.model.defectName || root.defectName
        font.pixelSize: 15
        anchors.left: parent.right
        background: Rectangle {
            color: root.style.infoOverlayColor
            border.color: root.style.infoOverlayBorderColor
            border.width: 1
            radius: 2
        }
    }
}
