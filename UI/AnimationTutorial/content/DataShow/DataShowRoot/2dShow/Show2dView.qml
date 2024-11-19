import QtQuick 2.15
import QtQuick.Controls 2.15
import Qt5Compat.GraphicalEffects
import "../Aerial"
import "../../../Base"
import "../../Comps"
import "Draw"
Item {
    id:root
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
            BackSvg{
                anchors.fill: parent
            }
            Image {
                cache: true
                width: parent.width
                height: parent.height
                fillMode: Image.PreserveAspectFit
                id: image
                asynchronous: true
                source:surfaceData.source
                onStatusChanged: {
                    if (status === Image.Ready) {
                        dataShowCore.sourceWidth = image.sourceSize.width
                        dataShowCore.sourceHeight = image.sourceSize.height
                    }
                }
            }
            Image {
                cache: true
                id: image2
                asynchronous: true
                source: surfaceData.source
                sourceSize.width:canvas.width
                sourceSize.height:canvas.height
            }
            GammaAdjust {
                     anchors.fill: image
                     source: image2
                     gamma: dataShowCore.image_gamma
                     enabled:visible
                     visible: dataShowCore.image_gamma_enable
                 }

            Image{
                id:image_show
                cache: true
                width: parent.width
                height: parent.height
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                source: surfaceData.error_source
                visible: surfaceData.error_visible && dataShowCore.image_gamma_enable
                enabled:visible
                opacity: surfaceData.tower_warning_show_opacity/100
            }
            ShowDefects{
            }
            DrawView{
            }
            TapHandler{
                acceptedButtons: Qt.LeftButton
                onDoubleTapped: {
                    surfaceData.p2 = Qt.point(dataShowCore.hoverdX,dataShowCore.hoverdY)
                    surfaceData.addSignPoint(
                                Qt.point(dataShowCore.hoverdX,dataShowCore.hoverdY)
                                )
                }
            }
            WheelHandler{  // 缩放
                target: image
                onWheel: (event)=> {
                             let hX = event.x-flick.contentX
                             let hY = event.y-flick.contentY
                             dataShowCore.scaleTempPoint = dataShowCore.getAspectRatioByPoint (Qt.point(hX,hY))
                             if (event.angleDelta.y > 0) {
                                dataShowCore.canvasScale *= 1.1
                             } else {
                                dataShowCore.canvasScale *= 0.9
                             }
                             if (dataShowCore.canvasScale > 1){
                                dataShowCore.canvasScale = dataShowCore.maxScale
                                dataShowCore.setMaxErrorScale("red")
                             }
                             else if (dataShowCore.canvasScale <= dataShowCore.minScale){

                                dataShowCore.canvasScale = dataShowCore.minScale
                                 dataShowCore.setMaxErrorScale("blue")
                             }
                             dataShowCore.setFlickablebyPoint(Qt.point(hX, hY))
                        }
            }
        }
    }
    ShowInfos{
        width: root.width
        height: root.height
    }
    CrossView{
        visible: dataShowCore.chartHovered | dataShowCore.imageShowHovered
        crossX:dataShowCore.hoverPoint.x
        crossY:dataShowCore.hoverPoint.y
    }
    AerialView{
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
}
