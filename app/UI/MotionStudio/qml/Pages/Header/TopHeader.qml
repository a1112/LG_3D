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
    id:root

    required property var adaptiveMetrics
    required property var style
    required property var modelStore
    required property var authManager
    required property var globalContext
    required property var coreController
    required property var appController
    required property var viewControl
    required property var popupManager

    Layout.fillWidth: true
    implicitHeight: root.style.topHeight
    implicitWidth: root.adaptiveMetrics.designWidth
    height: root.style.topHeight
    clip: false
    readonly property var appWindow: Window.window
    Pane{
        anchors.fill: parent
        Material.elevation: 5
        Material.background: root.style.headerBackgroundColor
    }
    Rectangle{
        anchors.fill: parent
        color: root.style.headerBackgroundColor
    }
    Rectangle{
        width: parent.width
        height: 1
        color: root.style.headerBorderColor
        anchors.bottom: parent.bottom
    }
    RowLayout{
        anchors.fill: parent
        spacing: root.adaptiveMetrics.headerSpacing
        Item{
            Layout.preferredWidth: root.adaptiveMetrics.headerSideGap
            Layout.preferredHeight: 1
        }
        ItemDelegateButtonBase {
          id: mainMenuButton
          Layout.preferredHeight: parent.height
          Layout.preferredWidth: parent.height
          tipText: qsTr("主菜单")
          source: root.style.getIcon("Menu")
        }

        TopIcon{}
        TopTabBar{
            adaptiveMetrics: root.adaptiveMetrics
            style: root.style
            appController: root.appController
        }
        SeparatorLine{}
        TopTools{
            adaptiveMetrics: root.adaptiveMetrics
            popupManager: root.popupManager
        }
        TopSettingButton{}

        Item{
            implicitWidth: root.adaptiveMetrics.headerLargeGap
            Layout.fillHeight: true
        }
        TopMsg{
            authManager: root.authManager
            modelStore: root.modelStore
            coreController: root.coreController
            globalContext: root.globalContext
        }
        FillLayout{
            GlobalErrorView{    // 全局报警
                anchors.centerIn: parent
            }
        }
        WindowTitleLabel{
            coreController: root.coreController
            style: root.style
            viewControl: root.viewControl
        }
        FillLayout{}
        GlobalServerMsg{}
        TimeText{
            visible: !root.authManager.isAdmin
                     || !root.globalContext.screenConfig.isMinScreen
        }
        FillLayout{}
        TopCoilTools{
            adaptiveMetrics: root.adaptiveMetrics
            modelStore: root.modelStore
            authManager: root.authManager
        }
        Item{
            implicitWidth: root.adaptiveMetrics.headerSideGap
            Layout.fillHeight: true
        }
        RowLayout{
            id: captionControls
            Layout.preferredHeight: parent.height
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignVCenter
            spacing: root.style.headerButtonGap
            HelpButton{
                Layout.alignment: Qt.AlignVCenter
                visible: !root.authManager.isAdmin
            }
            TopToolsButton{
                Layout.alignment: Qt.AlignVCenter
            }
            RowLayout {
                id: windowControls
                Layout.preferredWidth: root.style.windowButtonWidth * 3
                Layout.preferredHeight: root.style.topHeight
                Layout.alignment: Qt.AlignVCenter
                spacing: 0

                WindowCaptionButton {
                    id: minimizeButton
                    buttonType: "minimize"
                    tipText: qsTr("最小化")
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
                    tipText: qsTr("关闭")
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
