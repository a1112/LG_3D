
/*
    2D功能切换
*/
import QtQuick
import QtQuick.Layouts
import "V2D"
import "V3D"
ColumnLayout {
    id:root
    width: 300
    // height: width/dataShowCore.aspectRatio
        View3D{

            width:root.width
            Layout.fillHeight:true
        }
        View2D{
            width:root.width
            height:width
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