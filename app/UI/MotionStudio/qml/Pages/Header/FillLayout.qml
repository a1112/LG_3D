import QtQuick
import QtQuick.Layouts
import QtQuick.Window
Item{
    Layout.fillWidth: true
    Layout.fillHeight: true

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
            const window = Window.window
            if (active && window && window.startSystemMove) {
                window.startSystemMove()
            }
        }
    }
}
