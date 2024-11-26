import QtQuick
import QtQuick.Controls
ItemDelegate{
    height: 20
    font.pointSize: 15
    text: "缩放：" + ( dataShowCore.canvasScale*100).toFixed(0) + "%"
    onClicked: {
        menu_scale.popup()
    }
    Rectangle{
        anchors.fill: parent
        color:dataShowCore.errorScaleColor
        opacity: dataShowCore.errorScaleSignal?1:0
        Behavior on opacity {
            NumberAnimation {
                duration: 800
            }
        }
        Timer{
            interval: 800
            running:dataShowCore.errorScaleSignal
            onTriggered: {
                dataShowCore.errorScaleSignal = false
            }
        }
    }
}
