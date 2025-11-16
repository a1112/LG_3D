import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

BaseImage{
    id:root
    property bool effect: true
    property real horizontalOffset: 5
    property real verticalOffset: 5
    fillMode: Image.PreserveAspectFit
    layer.enabled: true
    layer.effect: DropShadowBase{
        id:drapShadow
        horizontalOffset:root.horizontalOffset
        verticalOffset:root.verticalOffset
        visible: effect
    }
    Behavior on scale {SmoothedAnimation{duration: 300}}
}
