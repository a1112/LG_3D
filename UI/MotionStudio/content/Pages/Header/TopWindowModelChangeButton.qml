import QtQuick.Window
import "../../btns"

WindowModelChangeButton {
    height: 35
    tipText: control.isFullScreen?"窗口模式":"全屏模式"
    selectColor:control.isFullScreen? "#FFCB3D":"#3DCBFF"
    onClicked: {
        control.visibility= control.isFullScreen? Window.Windowed:Window.FullScreen
    }
}
