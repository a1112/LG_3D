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
    }
    MaskTool{  // 遮挡
    }
}
