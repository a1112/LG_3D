import QtQuick
import QtQuick.Controls
ItemDelegate{
    height: 20
    font.pointSize: 15
    text: "缩放：" + ( dataShowCore_.canvasScale*100).toFixed(0) + "%"
    onClicked: {
        menu_scale.popup()
    }
    Rectangle{
        anchors.fill: parent
        color:dataShowCore_.errorScaleColor
        opacity: dataShowCore_.errorScaleSignal?1:0
        Behavior on opacity {
            NumberAnimation {
                duration: 800
            }
        }
        Timer{
            interval: 800
            running:dataShowCore_.errorScaleSignal
            onTriggered: {
                dataShowCore_.errorScaleSignal = false
            }
        }
    }
}
