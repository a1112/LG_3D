pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "OtherSetting"
import "GeneralSetting"
import "InfoSetting"
import "StyleSetting"
import "CameraSetting"

Popup {
    id: root
    required property var apiClient
    required property var style
    required property var settings
    required property var coreController
    required property var appInfo
    required property var downloadClient
    anchors.centerIn: parent
    width: Math.min(parent ? parent.width * 0.72 : 1040, 1120)
    height: Math.min(parent ? parent.height * 0.78 : 720, 760)
    padding: 0
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    Material.elevation: 12

    background: Rectangle {
        color: root.style.panelBackgroundColor
        border.color: root.style.headerBorderColor
        border.width: 1
        radius: 6
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 62
            color: root.style.headerBackgroundColor
            radius: 6

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: root.style.headerBorderColor
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 14
                spacing: 16

                Label {
                    text: qsTr("设置")
                    color: root.style.titleColor
                    font.pixelSize: 24
                    font.bold: true
                    Layout.alignment: Qt.AlignVCenter
                }

                Label {
                    text: qsTr("系统参数与显示配置")
                    color: root.style.labelColor
                    opacity: 0.78
                    font.pixelSize: 13
                    Layout.alignment: Qt.AlignVCenter
                }

                Item {
                    Layout.fillWidth: true
                }

                ToolButton {
                    id: closeButton
                    text: "x"
                    font.pixelSize: 18
                    font.bold: true
                    implicitWidth: 40
                    implicitHeight: 40
                    ToolTip.visible: hovered
                    ToolTip.text: qsTr("关闭")
                    onClicked: root.close()

                    background: Rectangle {
                        color: closeButton.hovered
                               ? root.style.statusErrorColor
                               : root.style.panelElevatedColor
                        radius: root.style.controlRadius
                    }

                    contentItem: Text {
                        text: closeButton.text
                        color: closeButton.hovered
                               ? "#FFFFFF" : root.style.labelColor
                        font: closeButton.font
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }

        TabBar {
            id: tabBar
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            background: Rectangle {
                color: root.style.panelBackgroundColor
            }

            Repeater {
                model: [
                    qsTr("常规"),
                    qsTr("风格"),
                    qsTr("相机调整"),
                    qsTr("信息"),
                    qsTr("其他")
                ]

                TabButton {
                    id: tabButton
                    required property string modelData
                    text: modelData
                    font.pixelSize: 14
                    contentItem: Text {
                        text: tabButton.text
                        color: tabButton.checked
                               ? root.style.titleColor : root.style.labelColor
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font: tabButton.font
                    }
                    background: Rectangle {
                        color: tabButton.checked
                               ? root.style.panelElevatedColor
                               : root.style.panelBackgroundColor
                        border.color: tabButton.checked
                                      ? root.style.titleColor
                                      : root.style.headerBorderColor
                        border.width: tabButton.checked ? 1 : 0
                        radius: root.style.controlRadius
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: root.style.headerBorderColor
        }

        StackLayout {
            Layout.fillHeight: true
            Layout.fillWidth: true
            currentIndex: tabBar.currentIndex
            clip: true

            GeneralSetting {
                settings: root.settings
                style: root.style
            }
            StyleSetting {
                style: root.style
            }
            CameraSetting {
                apiClient: root.apiClient
                style: root.style
            }
            InfoSetting {
                apiClient: root.apiClient
                settings: root.settings
                style: root.style
                coreController: root.coreController
            }
            OtherSetting {
                apiClient: root.apiClient
                style: root.style
                settings: root.settings
                appInfo: root.appInfo
                downloadClient: root.downloadClient
            }
        }
    }
}
