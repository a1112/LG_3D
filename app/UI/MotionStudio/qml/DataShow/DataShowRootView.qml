import QtQuick
import QtQuick.Layouts

Item{
    id: root
    required property var surface
    required property var modelStore
    required property var controller
    required property var style

    StackLayout{
        anchors.fill: parent
        currentIndex: root.surface.rootViewIndex
        Data2DLayout{
            surfaceData: root.surface
            dataShowCore: root.controller
            modelStore: root.modelStore
            style: root.style
        }

        Data3DLayout{
        }

        DataAreaLayout{    // 2D 图像的显示
        }

    }
    MaskTool{  // 遮挡
        controller: root.controller
        style: root.style
    }
}
