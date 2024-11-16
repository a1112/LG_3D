import QtQuick
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
Rectangle {
    layer.enabled: true
    property alias verticalOffset:drops.verticalOffset
    property alias horizontalOffset:drops.horizontalOffset
    DropShadowBase{
            id:drops
        }
    layer.effect:drops
}
