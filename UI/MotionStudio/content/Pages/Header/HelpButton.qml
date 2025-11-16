import QtQuick

ToolsButton{
   height:35
   width:height
   tipText: qsTr("帮助")
  source:"../icons/help.png"
  onClicked: popManage.popupHelpView()
}
