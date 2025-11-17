import QtQuick
import QtQuick.Layouts
import "2dShow"
import "2dShow/MaskTool"
Loader{
    active: surfaceData.is2DrootView
    Layout.fillWidth: true
    Layout.fillHeight:true
    asynchronous:true
    sourceComponent: Item{
        Layout.fillWidth: true
        Layout.fillHeight:true
        id: dataShow2DView
        Show2dView{}    // 2D 显示

        MaskToolView{}// 功能菜单
    }

}

