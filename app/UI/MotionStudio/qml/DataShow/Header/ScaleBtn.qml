import QtQuick
import QtQuick.Controls
ItemDelegate{
    id: root

    required property var controller
    required property var menuController

    height: 20
    font.pointSize: 15
    text: qsTr("缩放：%1%").arg((root.controller.canvasScale * 100).toFixed(0))
    onClicked: {
        root.menuController.popup()
    }
    Rectangle{
        anchors.fill: parent
        color: root.controller.errorScaleColor
        opacity: root.controller.errorScaleSignal ? 1 : 0
        Behavior on opacity {
            NumberAnimation {
                duration: 800
            }
        }
        Timer{
            interval: 800
            running: root.controller.errorScaleSignal
            onTriggered: {
                root.controller.errorScaleSignal = false
            }
        }
    }
}
