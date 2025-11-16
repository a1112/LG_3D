import QtQuick
import "../../../btns"
import "../../Header"
ImageButton{
    id:fliterBtn
    property bool selectd: leftCore.fliterEnable
    tipText:"筛选"
    opacity: leftCore.fliterEnable?1:0.65
    height: parent.height
    width: height
    source:coreStyle.isDark?coreStyle.getIcon("filter_light"):coreStyle.getIcon("filter")
    onClicked: leftCore.fliterEnable=!leftCore.fliterEnable
    Rectangle{
        visible:leftCore.fliterEnable
        width:parent.width
        height:5
        color:coreStyle.accentColor
        anchors.bottom:parent.bottom
    }
}
