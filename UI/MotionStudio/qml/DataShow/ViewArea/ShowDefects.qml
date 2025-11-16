import QtQuick
import QtQuick.Controls
Item {
    id:root
    anchors.fill: parent
    property var defects : []
    Repeater{
        id:repeater
        model: dataShowCore.areaDefectModel
        DefectShowItem{
        }
    }

}
