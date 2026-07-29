pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import ConsoleController 1.0
import "../Controls/Menu"

Menu {
    id: root

    required property var style
    required property var settings
    required property var popupManager
    required property var authManager
    required property var graphsManager
    required property var deviceCurveManager

    ConsoleController {
        id: consoleController
    }

    Menu {
        title: qsTr("主题")

        MenuItem {
            text: qsTr("黑色")
            onTriggered: root.style.applyTheme("dark")
        }
        MenuItem {
            text: qsTr("白色")
            onTriggered: root.style.applyTheme("light")
        }
        MenuItem {
            text: qsTr("蓝色")
            onTriggered: root.style.applyTheme("blue")
        }
    }

    Menu {
        title: qsTr("色彩设置")

        TextColorMenuItem {
            text: qsTr("主标题颜色")
            selectedColor: root.style.rootTitleColor
            onSelectedColorChanged:
                root.style.rootTitleColor = selectedColor
        }
        TextColorMenuItem {
            text: qsTr("标题颜色")
            selectedColor: root.style.titleColor
            onSelectedColorChanged:
                root.style.titleColor = selectedColor
        }
        TextColorMenuItem {
            text: qsTr("边框颜色")
            selectedColor: root.style.cardBorderColor
            onSelectedColorChanged:
                root.style.cardBorderColor = selectedColor
        }
        TextColorMenuItem {
            text: qsTr("前景色")
            selectedColor: root.style.accentColor
            onSelectedColorChanged:
                root.style.accentColor = selectedColor
        }
    }

    MenuItem {
        text: consoleController.isShow
              ? qsTr("隐藏控制台") : qsTr("显示控制台")
        onTriggered:
            consoleController.isShow = !consoleController.isShow
    }

    Menu {
        title: qsTr("图像模式")

        SelectMenuItem {
            style: root.style
            text: qsTr("共享文件夹模式")
            selectd: root.settings.useSharedFolder
            onTriggered: root.settings.useSharedFolder = true
        }
        SelectMenuItem {
            style: root.style
            text: qsTr("HTTP 模式")
            selectd: !root.settings.useSharedFolder
            onTriggered: root.settings.useSharedFolder = false
        }
    }

    Menu {
        title: qsTr("图像服务")

        SelectMenuItem {
            style: root.style
            text: qsTr("Python 服务 (6012)")
            selectd: !root.settings.useRustImageServer
            onTriggered: root.settings.useRustImageServer = false
        }
        SelectMenuItem {
            style: root.style
            text: qsTr("Rust 服务 (6013)")
            selectd: root.settings.useRustImageServer
            onTriggered: root.settings.useRustImageServer = true
        }
        MenuSeparator {}
        MenuItem {
            enabled: false
            text: root.settings.useRustImageServer
                  ? qsTr("当前: Rust / 端口 ")
                    + root.settings.rustImageServerPort
                  : qsTr("当前: Python / 端口 ")
                    + root.settings.imageServerPort
        }
    }

    MenuItem {
        text: qsTr("裁剪设置...")
        onTriggered: root.popupManager.popupClipSettingView()
    }

    Menu {
        title: qsTr("界面模式")

        Repeater {
            model: root.authManager.userModels

            SelectMenuItem {
                required property string name
                required property string key

                style: root.style
                text: name
                selectd: root.authManager.currentUser
                          && root.authManager.currentUser.key === key
                onTriggered: root.authManager.setUserKey(key)
            }
        }
    }

    Menu {
        title: qsTr("其他工具")

        MenuItem {
            text: qsTr("API 访问记录")
            onTriggered: root.popupManager.popupApiList()
        }
        MenuItem {
            text: qsTr("算法测试...")
            onTriggered: root.popupManager.popupAlgTestDialog()
        }
    }

    MenuItem {
        text: qsTr("设备曲线")
        onTriggered: root.deviceCurveManager.open()
    }

    MenuItem {
        text: qsTr("曲线工具")
        onTriggered: root.graphsManager.open()
    }
}
