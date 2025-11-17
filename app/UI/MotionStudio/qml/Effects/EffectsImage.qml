import QtQuick 2.15
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
Image {
    id: sourceImage
    property bool hovered: hoverHandler.hovered
    HoverHandler{
        id:hoverHandler
    }

    layer.enabled:true
    layer.effect:DropShadow {
        enabled:true
            horizontalOffset: 4
            verticalOffset: 4
            radius:6
            color: "#40000000"
        }
}
