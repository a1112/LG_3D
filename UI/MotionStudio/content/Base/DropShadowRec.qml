import QtQuick
Rectangle {
    id:rec
    layer.enabled: true
    property real verticalOffset:5
    property real horizontalOffset:5
    layer.effect:DropShadowBase{
        verticalOffset:rec.verticalOffset
        horizontalOffset:rec.horizontalOffset
    }
}
