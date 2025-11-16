import QtQuick

Item {
    anchors.fill: parent
    WheelHandler{  // 缩放

        onWheel: (event)=> {
                     let hX = event.x-flick.contentX
                     let hY = event.y-flick.contentY
                     dataAreaShowCore.scaleTempPoint = dataAreaShowCore.getAspectRatioByPoint (Qt.point(hX,hY))
                     if (event.angleDelta.y > 0) {
                        dataAreaShowCore.canvasScale *= 1.1
                     } else {
                        dataAreaShowCore.canvasScale *= 0.9
                     }
                     if (dataAreaShowCore.canvasScale > dataAreaShowCore.maxScale){
                        dataAreaShowCore.canvasScale = dataAreaShowCore.maxScale
                        dataShowCore.setMaxErrorScale("red")
                     }
                     else if (dataAreaShowCore.canvasScale <= dataAreaShowCore.minScale){

                        dataAreaShowCore.canvasScale = dataAreaShowCore.minScale
                         dataShowCore.setMaxErrorScale("blue")
                     }
                     dataAreaShowCore.setFlickablebyPoint(Qt.point(hX, hY))
                }
    }

}
