import QtQuick 2.15
import QtQuick.Dialogs
import QtQuick.Controls
import ConsoleController 1.0
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
        title:"主题"
        MenuItem{
            text:"深色"
            onTriggered: {
                coreStyle.isDark=true
            }
        }
        MenuItem{
            text:"浅色"
            onTriggered: {
                coreStyle.isDark=false
            }
        }
    }

    Menu{
        title:"色彩设置"
        TextColorMenuItem{
            text:"主标题颜色"
            selectedColor: coreStyle.rootTitleColor
            onSelectedColorChanged: {
                coreStyle.rootTitleColor=selectedColor
            }
        }
        TextColorMenuItem{
            text:"标题颜色"
            selectedColor: coreStyle.titleColor
            onSelectedColorChanged: {
                coreStyle.titleColor=selectedColor
            }
        }

        TextColorMenuItem{
            text:"边框颜色"
            selectedColor: coreStyle.cardBorderColor
            onSelectedColorChanged: {
                coreStyle.cardBorderColor=selectedColor
            }
        }

        TextColorMenuItem{
            text:"前景色"
            selectedColor: coreStyle.accentColor
            onSelectedColorChanged: {
                coreStyle.accentColor=selectedColor
            }
        }

    }

    MenuItem{
        text: consoleController.isShow ? "隐藏控制台" : "显示控制台"
        onClicked: consoleController.isShow = !consoleController.isShow
    }
    Menu{
        title:"图像模式"
        SelectMenuItem{
            text: "共享文件夹模式"
            selectd:coreSetting.useSharedFolder
            onClicked: coreSetting.useSharedFolder=true
        }
        SelectMenuItem{
            text: "HTTP模式"
            selectd:!coreSetting.useSharedFolder
            onClicked: coreSetting.useSharedFolder=false
        }
    }

    Menu{
        title:"界面模式"
        Repeater{
            model:auth.userModels
            SelectMenuItem{
                text: name
                selectd:auth.currentUser.key==key
                onClicked: auth.setUserByKey(key)
            }
        }
    }
    Menu{
        title:"其他工具"
        MenuItem{
            text:"API 访问记录"
            onClicked:{
                apiListPop.popup()
            }
        }
    }
}
