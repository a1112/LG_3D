import QtQuick
import "../Core/ViewportMath.js" as ViewportMath

Item {
    anchors.fill: parent
    WheelHandler{  // 缩放

        onWheel: function(event) {
            var boundary = ViewportMath.zoomAt(dataAreaShowCore,
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
