import QtQuick
import QtQuick.Dialogs
import QtQuick.Controls
import ConsoleController 1.0
import "../Controls/Menu"
Menu{

    property var colorFunc
    ConsoleController{
        id:consoleController
    }
    ColorDialog{
        id:colorDialog
        onAccepted:{
            colorFunc(colorDialog.selectedColor)
        }
    }


    Menu{
        title:qsTr("主题")
        MenuItem{
            text:qsTr("深色")
            onTriggered: {
                coreStyle.isDark=true
            }
        }
        MenuItem{
            text:qsTr("浅色")
            onTriggered: {
                coreStyle.isDark=false
            }
        }
    }

    Menu{
        title:qsTr("色彩设置")
        TextColorMenuItem{
            text:qsTr("主标题颜色")
            selectedColor: coreStyle.rootTitleColor
            onSelectedColorChanged: {
                coreStyle.rootTitleColor=selectedColor
            }
        }
        TextColorMenuItem{
            text:qsTr("标题颜色")
            selectedColor: coreStyle.titleColor
            onSelectedColorChanged: {
                coreStyle.titleColor=selectedColor
            }
        }

        TextColorMenuItem{
            text:qsTr("边框颜色")
            selectedColor: coreStyle.cardBorderColor
            onSelectedColorChanged: {
                coreStyle.cardBorderColor=selectedColor
            }
        }

        TextColorMenuItem{
            text:qsTr("前景色")
            selectedColor: coreStyle.accentColor
            onSelectedColorChanged: {
                coreStyle.accentColor=selectedColor
            }
        }

    }

    MenuItem{
        text: consoleController.isShow ? qsTr("隐藏控制台") : qsTr("显示控制台")
        onClicked: consoleController.isShow = !consoleController.isShow
    }
    Menu{
        title:qsTr("图像模式")
        SelectMenuItem{
            text: qsTr("共享文件夹模式")
            selectd:coreSetting.useSharedFolder
            onClicked: coreSetting.useSharedFolder=true
        }
        SelectMenuItem{
            text: qsTr("HTTP模式")
            selectd:!coreSetting.useSharedFolder
            onClicked: coreSetting.useSharedFolder=false
        }
    }

    Menu{
        title:qsTr("界面模式")
        Repeater{
            model:auth.userModels
            SelectMenuItem{
                text: name
                selectd:auth.currentUser.key==key
                onClicked: auth.setUserKey(key)
            }
        }
    }
    Menu{
        title:qsTr("其他工具")
        MenuItem{
            text:qsTr("API 访问记录")
            onClicked:{
                popManage.popupApiList()
            }
        }
    }
}
