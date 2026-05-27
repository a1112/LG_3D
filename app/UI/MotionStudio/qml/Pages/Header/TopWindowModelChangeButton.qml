import QtQuick.Window
import "../../btns"

WindowModelChangeButton {
    height: 35
    tipText: control.isMaximized || control.isFullScreen ? "还原" : "最大化"
    selectColor: control.isMaximized || control.isFullScreen ? "#FFCB3D" : "#3DCBFF"
    shouMaxIcon: !control.isMaximized && !control.isFullScreen
    onClicked: {
        control.visibility = control.isMaximized || control.isFullScreen ? Window.Windowed : Window.Maximized
    }
}
