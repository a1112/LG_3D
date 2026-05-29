import QtQuick

ToolsButton{
   height: coreStyle.topHeight
   width: coreStyle.windowButtonWidth
    tipText: "工具"
   onClicked:{
        popManage.popupToolsMenuView()
   }
}
