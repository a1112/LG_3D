
pragma ComponentBehavior: Bound

/*
    2D功能切换
*/
import QtQuick
import QtQuick.Layouts
import "V2D"
import "V3D"
ColumnLayout {
    id: root

    required property var adaptiveMetrics
    required property var surfaceData
    required property var dataShowCore
    required property var modelStore
    required property var view3DController
    required property var style

    width: root.adaptiveMetrics.mask_tool_width
    // height: width/dataShowCore.aspectRatio

        Loader{
            width: root.width
            Layout.fillHeight:true
            asynchronous: true
            active: root.surfaceData.meshExits
            sourceComponent:View3D{
                surfaceData: root.surfaceData
                dataShowCore: root.dataShowCore
                view3DController: root.view3DController
            }

        }

        View2D{
            surfaceData: root.surfaceData
            dataShowCore: root.dataShowCore
            modelStore: root.modelStore
            style: root.style
            width: root.width
            height: width
        }
//     Item{
//         implicitHeight:50
//         height: implicitHeight
//         Layout.fillWidth:true
//         width:root.width
//     ToolBoxView{
//         x:50
//         width: parent.width
//         height: parent.height
//     }
// }
    Item{
        implicitHeight:20
        height: implicitHeight
        Layout.fillWidth:true
        width:root.width
    }
}
