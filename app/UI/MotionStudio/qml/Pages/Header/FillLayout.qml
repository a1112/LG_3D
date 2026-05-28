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
            control.visibility = control.isFullScreen ? Window.Windowed : Window.FullScreen
        }
    }

    DragHandler {
        target: null
        acceptedButtons: Qt.LeftButton
        enabled: !control.isFullScreen
        onActiveChanged: {
            const window = root.appWindow
            if (active && window && window.startSystemMove) {
                window.startSystemMove()
            }
        }
    }
}
