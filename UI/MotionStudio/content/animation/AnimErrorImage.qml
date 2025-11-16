import QtQuick

Image {
    id:root
    property bool running: true

    ScaleAnimator{
        target: parent
        from: 0.8
        to: 1.5
        duration: 1000
        running: root.running
        onFinished: {
            let temp=from
            from=to
            to=temp
            restart()
        }
    }
}
