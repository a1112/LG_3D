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
    implicitWidth: adaptive.designWidth
    height: coreStyle.topHeight
    clip: false
    readonly property var appWindow: Window.window
    Pane{
        anchors.fill: parent
        Material.elevation: 5
        Material.background: coreStyle.headerBackgroundColor
    }
    Rectangle{
        anchors.fill: parent
        color: coreStyle.headerBackgroundColor
    }
    Rectangle{
        width: parent.width
        height: 1
        color: coreStyle.headerBorderColor
        anchors.bottom: parent.bottom
    }
    RowLayout{
        anchors.fill: parent
        spacing: adaptive.headerSpacing
        Item{
            Layout.preferredWidth: adaptive.headerSideGap
            Layout.preferredHeight: 1
        }
        ItemDelegateButtonBase {
          id: mainMenuButton
          Layout.preferredHeight: parent.height
          Layout.preferredWidth: parent.height
          tipText: qsTr("主菜单")
          source:  coreStyle.getIcon("Menu")
        }

        TopIcon{}
        TopTabBar{}
        SeparatorLine{}
        TopTools{}
        TopSettingButton{}

        Item{
            implicitWidth: adaptive.headerLargeGap
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
            implicitWidth: adaptive.headerSideGap
            Layout.fillHeight: true
        }
        RowLayout{
            id: captionControls
            Layout.preferredHeight: parent.height
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignVCenter
            spacing: coreStyle.headerButtonGap
            HelpButton{
                Layout.alignment: Qt.AlignVCenter
                visible: !auth.isAdmin
            }
            TopToolsButton{
                Layout.alignment: Qt.AlignVCenter
            }
            RowLayout {
                id: windowControls
                Layout.preferredWidth: coreStyle.windowButtonWidth * 3
                Layout.preferredHeight: coreStyle.topHeight
                Layout.alignment: Qt.AlignVCenter
                spacing: 0

                WindowCaptionButton {
                    id: minimizeButton
                    buttonType: "minimize"
                    tipText: "最小化"
                    onClicked: {
                        const window = root.appWindow
                        if (window) {
                            window.showMinimized()
                        }
                    }
                }
                TopWindowModelChangeButton {
                }
                WindowCaptionButton {
                    buttonType: "close"
                    tipText: "关闭"
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
}
