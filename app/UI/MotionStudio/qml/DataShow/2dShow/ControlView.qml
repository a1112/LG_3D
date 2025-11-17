import QtQuick 2.15

Item {
    anchors.fill: parent


    TapHandler{
        acceptedButtons: Qt.LeftButton
        enabled:dataShowCore.controls.isMoveModel
        onDoubleTapped: {
            surfaceData.p2 = Qt.point(dataShowCore.hoverdX,dataShowCore.hoverdY)
            surfaceData.addSignPoint(
                        Qt.point(dataShowCore.hoverdX,dataShowCore.hoverdY)
                        )
        }
    }

    TapHandler{
        acceptedButtons: Qt.LeftButton|Qt.RightButton
        enabled:dataShowCore.controls.isShowSurveyModel


        onTapped: (eventPoint, button)=> {
                      if (button==Qt.LeftButton){
                          dataShowCore.controls.setSurveyPoint(eventPoint.position)
                      }

                      console.log(
                                    "button", button,
                                    "@", eventPoint.position)
                  }

    }

    WheelHandler{  // 缩放

        onWheel: (event)=> {
                     let hX = event.x-flick.contentX
                     let hY = event.y-flick.contentY
                     dataShowCore.scaleTempPoint = dataShowCore.getAspectRatioByPoint (Qt.point(hX,hY))
                     if (event.angleDelta.y > 0) {
                        dataShowCore.canvasScale *= 1.1
                     } else {
                        dataShowCore.canvasScale *= 0.9
                     }
                     if (dataShowCore.canvasScale > dataShowCore.maxScale){
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
