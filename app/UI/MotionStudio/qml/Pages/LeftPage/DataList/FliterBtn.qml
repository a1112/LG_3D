import QtQuick
import "../../../btns"
import "../../Header"
ImageButton{
    id: root

    required property var style
    required property var leftController

    readonly property bool selected: root.leftController.fliterEnable
    tipText:"筛选"
    opacity: root.selected ? 1 : 0.65
    height: parent.height
    width: height
    source: root.style.isDark ? root.style.getIcon("filter_light")
                              : root.style.getIcon("filter")
    onClicked: root.leftController.fliterEnable = !root.leftController.fliterEnable
    Rectangle{
        visible: root.selected
        width:parent.width
        height:5
        color: root.style.accentColor
        anchors.bottom:parent.bottom
    }
}
