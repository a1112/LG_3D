import QtQuick

ToolsButton{
   height:35
   width:height
    tipText: "工具"
   onClicked:{
        popManage.popupToolsMenuView()
   }
}
