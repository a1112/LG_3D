pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
Item {
    id: root
    required property var controller
    required property var defectClassController
    required property var style
    anchors.fill: parent
    Repeater {
        model: root.controller.areaDefectModel
        DefectShowItem {
            controller: root.controller
            defectClassController: root.defectClassController
            style: root.style
        }
    }
}
