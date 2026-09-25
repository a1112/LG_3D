import QtQuick 2.15
import "../Core/ViewportMath.js" as ViewportMath

Item {
    id: root
    required property var controller
    required property var surfaceData
    required property var flickable
    required property var style

    anchors.fill: parent


    TapHandler{
        acceptedButtons: Qt.LeftButton
        enabled: root.controller.controls.isMoveModel
        onDoubleTapped: {
            root.surfaceData.p2 = Qt.point(root.controller.hoverdX, root.controller.hoverdY)
            root.surfaceData.addSignPoint(
                        Qt.point(root.controller.hoverdX, root.controller.hoverdY)
                        )
        }
    }

    TapHandler{
        acceptedButtons: Qt.LeftButton|Qt.RightButton
        enabled: root.controller.controls.isShowSurveyModel


        onTapped: (eventPoint, button)=> {
                      if (button==Qt.LeftButton){
                          root.controller.controls.setSurveyPoint(eventPoint.position)
                      }

                      console.log(
                                    "button", button,
                                    "@", eventPoint.position)
                  }

    }

    WheelHandler{  // 缩放

        onWheel: function(event) {
            var boundary = ViewportMath.zoomAt(root.controller,
                                               root.flickable,
                                               event.x,
                                               event.y,
                                               event.angleDelta.y)
            if (boundary > 0) {
                root.controller.setMaxErrorScale(root.style.statusErrorColor)
            } else if (boundary < 0) {
                root.controller.setMaxErrorScale(root.style.accentColor)
            }
            event.accepted = true
        }
    }

}
