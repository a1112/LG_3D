import QtQuick
import QtQuick.Controls
Image {
    id:root
    property bool running: false

    NumberAnimation on scale {
        from: 0.7; to: 1
        running:root.running
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
        running: root.running
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



}
