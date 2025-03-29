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
        DataAreaLayout{
        }
    }
    MaskTool{  // 遮挡
    }
}
