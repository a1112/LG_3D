import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Label {
    id: root

    required property var coreController
    required property var style
    required property var viewControl

    Layout.alignment: Qt.AlignVCenter
    text: root.coreController.appTitle
    font: Qt.font({
        family: "Inter",
        pixelSize: root.style.titleFontSize,
        bold: true
    })
    color: root.style.rootTitleColor
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
