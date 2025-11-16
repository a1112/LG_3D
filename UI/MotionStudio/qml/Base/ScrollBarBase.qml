

import QtQuick 2.12
import QtQuick.Templates 2.12 as T
import QtQuick.Controls.Universal 2.12

T.ScrollBar {
    id: control
    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    visible: control.policy !== T.ScrollBar.AlwaysOff

    // TODO: arrows

    contentItem: Rectangle {
        implicitWidth: control.interactive ? 12 : 6
        implicitHeight: control.interactive ? 12: 6
        color: control.pressed ? "#FF6A1D" :
               control.interactive && control.hovered ? "#FF921D" : "#C96800"
    }

    background: Rectangle {
        implicitWidth: control.interactive ? 12 : 6
        implicitHeight: control.interactive ? 12: 6
        color: control.Universal.chromeLowColor
        visible: control.size < 1.0
        opacity: 0.0
    }

    states: [
        State {
            name: "active"
            when: control.policy === T.ScrollBar.AlwaysOn || (control.active && control.size < 1.0)
        }
    ]

    transitions: [
        Transition {
            to: "active"
            NumberAnimation { targets: [contentItem, background]; property: "opacity"; to: 1.0 }
        },
        Transition {
            from: "active"
            SequentialAnimation {
                PropertyAction{ targets: [contentItem, background]; property: "opacity"; value: 1.0 }
                PauseAnimation { duration: 3000 }
                NumberAnimation { targets: [contentItem, background]; property: "opacity"; to: 0.0 }
            }
        }
    ]
}
