import QtQuick
import QtQuick.Layouts
import "2dShow"
import "2dShow/MaskTool"
Item {
    width:700
    height:1000
    Layout.fillWidth: true
    Layout.fillHeight:true
    Item{
        anchors.fill: parent
        id: dataShow2DView
        Show2dView{}
        MaskToolView{}// 功能菜单
    }
}
