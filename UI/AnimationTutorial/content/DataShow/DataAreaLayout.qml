import QtQuick
import QtQuick.Layouts
import "ViewArea"
import "Core"
import "2dShow/MaskTool"

Loader{
    active: surfaceData.isAreaRootView
    Layout.fillWidth: true
    Layout.fillHeight:true
property DataShowAreaCore dataAreaShowCore:dataShowCore.dataShowAreaCore
    sourceComponent: Item{
    Layout.fillWidth: true
    Layout.fillHeight:true
    id: dataShow2DView
        ViewArea{}
        // Show2dView{}    // 2D 显示
        // MaskToolView{}// 功能菜单
            MaskToolView{}// 功能菜单
    }

}
