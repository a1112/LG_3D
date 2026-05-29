import QtQuick
import QtQuick.Layouts
import QtQuick.Window
Item{
    id: root
    Layout.fillWidth: true
    Layout.fillHeight: true
    readonly property var appWindow: Window.window

    TapHandler {
        acceptedButtons: Qt.LeftButton
        gesturePolicy: TapHandler.ReleaseWithinBounds
        onDoubleTapped: {
            control.visibility = control.isMaximized ? Window.Windowed : Window.Maximized
        }
    }

    DragHandler {
        target: null
        acceptedButtons: Qt.LeftButton
        enabled: !control.isFullScreen
        onActiveChanged: {
            const window = root.appWindow
            if (active && window && window.startSystemMove) {
                if (control.isMaximized) {
                    control.visibility = Window.Windowed
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
