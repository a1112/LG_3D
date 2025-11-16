import QtQuick
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
Label{
    font.family: "Microsoft YaHei"
    font.pixelSize: 18
    font.bold: true
    layer.enabled: true
    layer.effect: DropShadow{
            enabled:true
            horizontalOffset: 3
            verticalOffset: 3
            radius:3
            color: "#80000000"
        }
    ItemDelegate{
        anchors.fill: parent
    }
}
