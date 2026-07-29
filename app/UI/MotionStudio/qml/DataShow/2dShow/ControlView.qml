import QtQuick 2.15
import "../Core/ViewportMath.js" as ViewportMath

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

        onWheel: function(event) {
            var boundary = ViewportMath.zoomAt(dataShowCore,
                                               flick,
                                               event.x,
                                               event.y,
                                               event.angleDelta.y)
            if (boundary > 0) {
                dataShowCore.setMaxErrorScale("red")
            } else if (boundary < 0) {
                dataShowCore.setMaxErrorScale("blue")
            }
            event.accepted = true
        }
    }

}
