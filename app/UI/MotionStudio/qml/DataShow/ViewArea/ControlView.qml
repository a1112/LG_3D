import QtQuick
import "../Core/ViewportMath.js" as ViewportMath

Item {
    id: root
    required property var controller
    required property var flickable
    required property var style

    anchors.fill: parent
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
