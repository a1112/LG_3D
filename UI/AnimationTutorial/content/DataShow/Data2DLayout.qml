import QtQuick
import QtQuick.Layouts
import "2dShow"
import "2dShow/MaskTool"

Item{
    Layout.fillWidth: true
    Layout.fillHeight:true
    id: dataShow2DView
    Show2dView{}    // 2D 显示

    MaskToolView{}// 功能菜单
}

