import QtQuick.Window

WindowCaptionButton {
    id: root

    required property var viewControl

    buttonType: root.viewControl.isMaximized || root.viewControl.isFullScreen
                ? "restore" : "maximize"
    tipText: root.viewControl.isMaximized || root.viewControl.isFullScreen
             ? qsTr("还原") : qsTr("最大化")
    onClicked: {
        root.viewControl.visibility =
                root.viewControl.isMaximized || root.viewControl.isFullScreen
                ? Window.Windowed : Window.Maximized
    }
}
