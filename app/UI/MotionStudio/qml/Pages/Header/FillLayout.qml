import QtQuick
import QtQuick.Layouts
import QtQuick.Window
Item{
    id: root
    required property var viewControl
    Layout.fillWidth: true
    Layout.fillHeight: true
    readonly property var appWindow: Window.window

    TapHandler {
        acceptedButtons: Qt.LeftButton
        gesturePolicy: TapHandler.ReleaseWithinBounds
        onDoubleTapped: {
            root.viewControl.visibility = root.viewControl.isMaximized
                    ? Window.Windowed : Window.Maximized
        }
    }

    DragHandler {
        target: null
        acceptedButtons: Qt.LeftButton
        enabled: !root.viewControl.isFullScreen
        onActiveChanged: {
            const window = root.appWindow
            if (active && window && window.startSystemMove) {
                if (root.viewControl.isMaximized) {
                    root.viewControl.visibility = Window.Windowed
                    Qt.callLater(function() {
                        if (window.startSystemMove) {
                            window.startSystemMove()
                        }
                    })
                } else {
                    window.startSystemMove()
                }
            }
        }
    }
}
