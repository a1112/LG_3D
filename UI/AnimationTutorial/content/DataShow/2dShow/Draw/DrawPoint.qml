import QtQuick
import QtQuick.Controls
Item {
    anchors.fill:parent
    Repeater{
        model:dataShowCore.pointData
        delegate:PointViewItem{
        }
    }
}
