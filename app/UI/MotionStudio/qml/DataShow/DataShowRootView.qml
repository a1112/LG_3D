import QtQuick
import QtQuick.Layouts

Item{
    id: root
    required property var surface
    required property var modelStore
    required property var controller
    required property var style
    required property var apiClient
    required property var globalContext

    StackLayout{
        anchors.fill: parent
        currentIndex: root.surface.rootViewIndex
        Data2DLayout{
            surfaceData: root.surface
            dataShowCore: root.controller
            modelStore: root.modelStore
            style: root.style
            apiClient: root.apiClient
        }

        Data3DLayout{
        }

        DataAreaLayout{    // 2D 图像的显示
            surfaceData: root.surface
            dataShowCore: root.controller
            modelStore: root.modelStore
            style: root.style
        }

    }
    MaskTool{  // 遮挡
        controller: root.controller
        style: root.style
        surfaceData: root.surface
        globalContext: root.globalContext
    }
}
