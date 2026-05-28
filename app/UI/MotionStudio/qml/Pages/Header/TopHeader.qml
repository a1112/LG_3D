import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Window
// import Qt5Compat.GraphicalEffects
// import "../../Base" as Base
import "../../btns"
// import "../../DataShow/Foot"
import "../../GlobalView"
import "../../Base"
Item {
    Layout.fillWidth: true
    implicitHeight: coreStyle.topHeight

    id:root
    width: 1080
    height: 35
    clip: false
    readonly property var appWindow: Window.window
    Pane{
        anchors.fill: parent
        Material.elevation: 5
    }
    Rectangle{
        color:"blue"
        anchors.fill: parent
        opacity:0.1
    }
    Rectangle{
        width: parent.width
        height: 1
                opacity:0.1
        color: "#FFF"
        anchors.bottom: parent.bottom
    }
    RowLayout{
        anchors.fill: parent
        spacing: 10
        Item{
            Layout.preferredWidth: 1
            Layout.preferredHeight: 1
        }
        ItemDelegateButtonBase {
          id: mainMenuButton
          height: parent.height
          width: height
          tipText: qsTr("主菜单")
          source:  coreStyle.getIcon("Menu")
          onClicked: {
              popManage.popupStyleMenu()
          }
        }

        TopIcon{}
        TopTabBar{}
        SeparatorLine{}
        TopTools{}
        TopSettingButton{}

        Item{
            implicitWidth: 50
            Layout.fillHeight: true
        }
        TopMsg{}
        FillLayout{
            GlobalErrorView{    // 全局报警
                anchors.centerIn: parent
            }
        }
        TitleLabel{}
        FillLayout{}
        GlobalServerMsg{}
        TimeText{
            visible: !auth.isAdmin || !global.screenConfig.isMinScreen
        }
        FillLayout{}
        TopCoilTools{}
        Item{
            implicitWidth: 20
            Layout.fillHeight: true
        }
        Row{
            spacing: 6
            HelpButton{
                visible: !auth.isAdmin
            }
            TopToolsButton{}
            ItemDelegate {
                id: minimizeButton
                height: 35
                width: height
                ToolTip.visible: hovered
                ToolTip.text: "最小化"
                onClicked: {
                    const window = root.appWindow
                    if (window) {
                        window.showMinimized()
                    }
                }
                background: Rectangle {
                    color: minimizeButton.hovered ? "#22FFFFFF" : "#00000000"
                }
                Label {
                    anchors.centerIn: parent
                    text: "-"
                    color: coreStyle.labelColor
                    font.pixelSize: 24
                    font.bold: true
                }
            }
            TopWindowModelChangeButton {}
            ItemDelegateButtonBase {
                height: 35
                width: height
                tipText: "关闭"
                source: coreStyle.getIcon("close")
                onClicked: {
                    const window = root.appWindow
                    if (window) {
                        window.close()
                    }
                }
            }
        }


}
}
