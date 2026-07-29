import QtQuick

ToolsButton{
    id: root

    required property var style
    required property var popupManager

    height: root.style.topHeight
    width: root.style.windowButtonWidth
    source: root.style.getIcon("tool")
    tipText: qsTr("工具")
    onClicked: root.popupManager.popupToolsMenuView()
}
