import QtQuick
import "../../btns" as Buttons

Buttons.ToolsButton{
    id: root

    required property var style
    required property var popupManager

    height: root.style.topHeight
    width: root.style.windowButtonWidth
    tipText: qsTr("帮助")
    source: root.style.getIcon("help")
    onClicked: root.popupManager.popupHelpView()
}
