import QtQuick
import QtQuick.Controls


ListView {
    add: Transition {
        NumberAnimation {
            property: "opacity"
            from: 0
            to: 1
            duration: 140
        }
    }

    spacing: 3
    reuseItems: true
    cacheBuffer: Math.max(240, height)
    boundsBehavior: Flickable.StopAtBounds
    highlightMoveDuration: 120
    ScrollBar.vertical: ScrollBar {
        policy: ScrollBar.AsNeeded
    }
}
