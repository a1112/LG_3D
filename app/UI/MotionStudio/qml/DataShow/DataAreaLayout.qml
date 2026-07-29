pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import "ViewArea"
import "Core"
import "2dShow/MaskTool"

Loader{
    id: root

    required property var surfaceData
    required property var dataShowCore
    required property var modelStore
    required property var style

    active: root.surfaceData.isAreaRootView
    Layout.fillWidth: true
    Layout.fillHeight:true
    property DataShowAreaCore dataAreaShowCore: root.dataShowCore.dataShowAreaCore
    sourceComponent: Item{
    Layout.fillWidth: true
    Layout.fillHeight:true
    id: dataShow2DView
        ViewArea{
            dataAreaShowCore: root.dataAreaShowCore
        }  // 显示主菜单
        // Show2dView{}    // 2D 显示
        // MaskToolView{}// 功能菜单
        MaskToolView{
            controller: root.dataAreaShowCore
            modelStore: root.modelStore
            surfaceData: root.surfaceData
            style: root.style
        }// 功能菜单
    }

}
