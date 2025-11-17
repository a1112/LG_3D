import QtQuick
import QtQuick.Layouts

Item{

    StackLayout{
        anchors.fill: parent
        currentIndex:root.surfaceData.rootViewIndex
        Data2DLayout{
        }

        Data3DLayout{
        }

        DataAreaLayout{    // 2D 图像的显示
        }

    }
    MaskTool{  // 遮挡
    }
}
