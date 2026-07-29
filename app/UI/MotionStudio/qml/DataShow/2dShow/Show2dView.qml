import QtQuick
import QtQuick.Controls
import "../Aerial"
import "Draw"
import "../Comps"
Item {
    id:root
    required property var surfaceData
    required property var dataShowCore
    required property var modelStore
    required property var style
    required property var apiClient

    anchors.fill: parent
    Rectangle{
    color: root.style.viewportBackgroundColor
    anchors.fill: parent
    }

    Flickable{
        id:flick
        clip: true
        anchors.fill: parent
        contentWidth: root.dataShowCore.canvasContentWidth
        contentHeight: root.dataShowCore.canvasContentHeight
        Component.onCompleted: {
            root.dataShowCore.flick = this
        }
        ScrollBar.vertical: ScrollBar {
            id:scrollBarV
        }
        ScrollBar.horizontal: ScrollBar {
            id:scrollBarH
        }
        Item{

            id:canvas
            width: root.dataShowCore.canvasContentWidth
            height: root.dataShowCore.canvasContentHeight

            ImageView{
            }
            ShowDefects{ // 缺陷绘制
            }
            DrawView{
                surfaceData: root.surfaceData
                dataShowCore: root.dataShowCore
                style: root.style
                apiClient: root.apiClient
            }
            ControlView{
            // 控制系统
            }


        }


    }
    CrossView{
        visible: root.dataShowCore.chartHovered
                 || root.dataShowCore.imageShowHovered
        dataShowCore: root.dataShowCore
        surfaceData: root.surfaceData
        style: root.style
        crossX: root.dataShowCore.hoverPoint.x
        crossY: root.dataShowCore.hoverPoint.y
    }

    AerialView{// 鸟亏图
        source: root.dataShowCore.source
        y:root.height - height-scrollBarH.height
    }
    HoverHandler{
        id:hoverHandler
        onHoveredChanged: root.dataShowCore.imageShowHovered = hovered
        onPointChanged: {
            var deltaX = Math.abs(
                        root.dataShowCore.hoverPoint.x - point.position.x)
            var deltaY = Math.abs(
                        root.dataShowCore.hoverPoint.y - point.position.y)
            if (deltaX < 2 && deltaY < 2) {
                return
            }
            if (deltaX > 5 || deltaY > 5) {
                root.modelStore.setKeepLatest(false)
            }
            root.dataShowCore.hoverPoint = point.position
        }
    }
}
