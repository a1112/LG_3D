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
    required property var settings
    required property var view3DController
    required property var adaptiveMetrics

    StackLayout{
        anchors.fill: parent
        currentIndex: root.surface.rootViewIndex
        Data2DLayout{
            surfaceData: root.surface
            dataShowCore: root.controller
            modelStore: root.modelStore
            style: root.style
            apiClient: root.apiClient
            globalContext: root.globalContext
        }

        Data3DLayout{
            surfaceData: root.surface
            dataShowCore: root.controller
            view3DController: root.view3DController
            style: root.style
        }

        DataAreaLayout{    // 2D 图像的显示
            surfaceData: root.surface
            dataShowCore: root.controller
            modelStore: root.modelStore
            style: root.style
            globalContext: root.globalContext
            apiClient: root.apiClient
            settings: root.settings
        }

    }
    MaskTool{  // 遮挡
        controller: root.controller
        style: root.style
        surfaceData: root.surface
        globalContext: root.globalContext
        adaptiveMetrics: root.adaptiveMetrics
        modelStore: root.modelStore
        view3DController: root.view3DController
    }
}
