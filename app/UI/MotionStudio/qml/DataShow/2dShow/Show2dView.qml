import QtQuick
import QtQuick.Controls
import "../Aerial"
import "Draw"
import "../Comps"
import "ViewTool"
Item {
    id:root
    anchors.fill: parent
    Rectangle{
    color: "black"
    anchors.fill: parent
    }

    Flickable{
        id:flick
        clip: true
        anchors.fill: parent
        contentWidth: dataShowCore.canvasContentWidth
        contentHeight: dataShowCore.canvasContentHeight
        Component.onCompleted: {
            dataShowCore.flick = this
        }
        ScrollBar.vertical: ScrollBar {
            id:scrollBarV
        }
        ScrollBar.horizontal: ScrollBar {
            id:scrollBarH
        }
        Item{

            id:canvas
            width: dataShowCore.canvasContentWidth
            height: dataShowCore.canvasContentHeight

            ImageView{
            }
            ShowDefects{ // 缺陷绘制
            }
            DrawView{
                // 绘制
            }
            ControlView{
            // 控制系统
            }


        }


    }
    CrossView{
        visible: dataShowCore.chartHovered | dataShowCore.imageShowHovered
        crossX:dataShowCore.hoverPoint.x
        crossY:dataShowCore.hoverPoint.y
    }

    AerialView{// 鸟亏图
        source: dataShowCore.source
        y:root.height - height-scrollBarH.height
    }
    HoverHandler{
        id:hoverHandler
        onHoveredChanged: dataShowCore.imageShowHovered=hovered
        onPointChanged: {
            if (Math.abs(dataShowCore.hoverPoint.x-point.position.x>5))
                coreModel.setKeepLatest(false)
            dataShowCore.hoverPoint = point.position
        }
    }

    Component.onCompleted:{
        dataShowCore.view2DTool = root.view2DTool
    }
}
