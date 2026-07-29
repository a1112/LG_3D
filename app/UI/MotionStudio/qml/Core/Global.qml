import QtQuick
import "../Property"
import "../types"
Item {
    id: root

    required property var style

    property DefectClassProperty defectClassProperty: DefectClassProperty {
        style: root.style
    }

    property ScreenConfig screenConfig:ScreenConfig{}
}
