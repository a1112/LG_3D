import QtQuick

ToolsButton{
   height:35
   width:height
   tipText: qsTr("帮助")
  source: coreStyle.getIcon("help")
  onClicked: popManage.popupHelpView()
}
