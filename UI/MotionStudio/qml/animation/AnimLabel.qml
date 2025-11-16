import QtQuick
import QtQuick.Controls
Label {
    ScaleAnimator{
        target: parent
        from: 0.9
        to: 1.1
        duration: 1500
        running: true
        onFinished: {
            let temp=from
            from=to
            to=temp
            restart()
        }
    }
}
