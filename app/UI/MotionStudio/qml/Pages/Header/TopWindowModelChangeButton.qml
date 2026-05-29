import QtQuick.Window

WindowCaptionButton {
    buttonType: control.isMaximized || control.isFullScreen ? "restore" : "maximize"
    tipText: control.isMaximized || control.isFullScreen ? "还原" : "最大化"
    onClicked: {
        control.visibility = control.isMaximized || control.isFullScreen ? Window.Windowed : Window.Maximized
    }
}
