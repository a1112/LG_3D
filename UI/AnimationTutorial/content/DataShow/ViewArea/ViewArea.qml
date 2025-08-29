import QtQuick
import QtQuick.Controls
import "../Aerial"
import "Draw"
import "../Comps"
import "ViewTool"
Item {
    id:root
    anchors.fill: parent
    property View2DTool view2DTool: View2DTool{}


    Flickable{
        id:flick
        clip: true
        anchors.fill: parent
        contentWidth: dataAreaShowCore.canvasContentWidth
        contentHeight: dataAreaShowCore.canvasContentHeight
        Component.onCompleted: {
            dataAreaShowCore.flick = this
        }
        ScrollBar.vertical: ScrollBar {
            id:scrollBarV
        }
        ScrollBar.horizontal: ScrollBar {
            id:scrollBarH
        }
        Item{
            id:canvas
            width: dataAreaShowCore.canvasContentWidth
            height: dataAreaShowCore.canvasContentHeight

            ImageView{}

            ShowDefects{ // 缺陷绘制
            }
            // DrawView{
            //     // 绘制
            // }
            ControlView{
            // 控制系统
            }
        }

    }

    AerialView{// 鸟亏图
        source: dataAreaShowCore.pre_source  // 缩略图像
        y:root.height - height-scrollBarH.height
    }


}
