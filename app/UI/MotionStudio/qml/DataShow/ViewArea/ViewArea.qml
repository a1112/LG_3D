import QtQuick
import QtQuick.Controls
import "../Aerial"
import "../Comps"
import "ViewTool"
Item {
    id:root

    required property var dataAreaShowCore

    anchors.fill: parent


    Flickable{
        id:flick
        clip: true
        anchors.fill: parent
        contentWidth: root.dataAreaShowCore.canvasContentWidth
        contentHeight: root.dataAreaShowCore.canvasContentHeight
        Component.onCompleted: {
            root.dataAreaShowCore.flick = this
        }
        ScrollBar.vertical: ScrollBar {
            id:scrollBarV
        }
        ScrollBar.horizontal: ScrollBar {
            id:scrollBarH
        }
        Item{
            id:canvas
            width: root.dataAreaShowCore.canvasContentWidth
            height: root.dataAreaShowCore.canvasContentHeight

            ImageView{}

            ShowDefects{ // 缺陷绘制
            }
            ControlView{
            // 控制系统
            }
        }

    }

    AerialView{// 鸟亏图
        source: root.dataAreaShowCore.pre_source  // 缩略图像
        y:root.height - height-scrollBarH.height
    }


}
