import QtQuick
import "../Base"
Rectangle {
    id:root
    property bool running: false

    property bool runningScale:root.running
    property bool runningOpacity:root.running

    property real scaleFrom: 0.7
    property real scaleTo: 1

    NumberAnimation on scale {
        from: 0.7; to: 1
        running:root.runningScale
        duration: 400
        easing.type: Easing.InOutElastic
        onFinished: {
            if (root.running) {
                from=0.7
            }
            else{
                from=1
            }
            restart()
        }
    }
    NumberAnimation on opacity {
        from: 0; to: 1
        running:root.runningOpacity
        duration: 400 // 动画持续时间（毫秒）
        easing.type: Easing.InOutElastic  // 缓动函数
        onFinished: {
            if (root.running) {
                from=0.1
            }
            else{
                from=1
            }
            restart()
        }

    }

    layer.enabled: true
    layer.effect:DropShadowBase{
    }
}
