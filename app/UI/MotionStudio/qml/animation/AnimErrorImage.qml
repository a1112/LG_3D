import QtQuick

Image {
    id: root
    property bool running: true

    SequentialAnimation {
        running: root.running && root.visible
        loops: Animation.Infinite

        ScaleAnimator {
            target: root
            from: 0.8
            to: 1.2
            duration: 700
            easing.type: Easing.InOutQuad
        }

        ScaleAnimator {
            target: root
            from: 1.2
            to: 0.8
            duration: 700
            easing.type: Easing.InOutQuad
        }
    }
}
