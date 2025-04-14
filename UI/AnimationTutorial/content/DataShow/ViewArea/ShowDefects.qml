import QtQuick
import QtQuick.Controls
Item {
    id:root
    anchors.fill: parent
    property var defects : []
    Repeater{
        model: dataShowCore.defectModel
        DefectShowItem{
        }
    }

}
