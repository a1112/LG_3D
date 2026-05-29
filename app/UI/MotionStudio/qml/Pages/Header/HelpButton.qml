import QtQuick

ToolsButton{
   height: coreStyle.topHeight
   width: coreStyle.windowButtonWidth
   tipText: qsTr("帮助")
  source: coreStyle.getIcon("help")
  onClicked: popManage.popupHelpView()
}
