import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Window
Label {
    Layout.alignment:Qt.AlignVCenter
    text: core.appTitle
    font.pixelSize: 24
    font.bold: true
    font.family: "Inter"
    color: coreStyle.rootTitleColor

    // Gradient {
    //     GradientStop { position: 0.0; color: "#333333" }
    //     GradientStop { position: 1.0; color: "#666666" }
    // }

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
