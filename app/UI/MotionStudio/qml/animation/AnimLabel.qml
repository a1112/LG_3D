import QtQuick
import QtQuick.Controls

Label {
    id: root
    property bool running: true

    SequentialAnimation {
        running: root.running && root.visible
        loops: Animation.Infinite

        ScaleAnimator {
            target: root
            from: 0.9
            to: 1.1
            duration: 1500
            easing.type: Easing.InOutQuad
        }

        ScaleAnimator {
            target: root
            from: 1.1
            to: 0.9
            duration: 1500
            easing.type: Easing.InOutQuad
        }
    }
}
