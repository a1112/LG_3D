pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import "2dShow"
import "2dShow/MaskTool"
Loader{
    id: root

    required property var surfaceData
    required property var dataShowCore
    required property var modelStore
    required property var style
    required property var apiClient

    active: root.surfaceData.is2DrootView
    Layout.fillWidth: true
    Layout.fillHeight:true
    asynchronous:true
    sourceComponent: Item{
        Layout.fillWidth: true
        Layout.fillHeight:true
        id: dataShow2DView
        Show2dView{
            surfaceData: root.surfaceData
            dataShowCore: root.dataShowCore
            modelStore: root.modelStore
            style: root.style
            apiClient: root.apiClient
        }    // 2D 显示

        MaskToolView{
            controller: root.dataShowCore
            modelStore: root.modelStore
            surfaceData: root.surfaceData
            style: root.style
        }// 功能菜单
    }

}

