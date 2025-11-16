import QtQuick

Item {
    anchors.fill:parent
    Repeater{
        model:dataShowCore.pointUserData
        delegate:PointViewItem{
        }
    }
}
