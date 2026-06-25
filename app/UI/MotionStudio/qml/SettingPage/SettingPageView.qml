import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "OtherSetting"
import "D3Setting"
import "GeneralSetting"
import "AlarmSetting"
import "InfoSetting"
import "StyleSetting"
import "CameraSetting"

Popup {
    id: root
    anchors.centerIn: parent
    width: Math.min(parent ? parent.width * 0.72 : 1040, 1120)
    height: Math.min(parent ? parent.height * 0.78 : 720, 760)
    padding: 0
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    Material.elevation: 12

    background: Rectangle {
        color: coreStyle.panelBackgroundColor
        border.color: coreStyle.headerBorderColor
        border.width: 1
        radius: 6
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 62
            color: coreStyle.headerBackgroundColor
            radius: 6

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: coreStyle.headerBorderColor
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 14
                spacing: 16

                Label {
                    text: qsTr("设置")
                    color: coreStyle.titleColor
                    font.pixelSize: 24
                    font.bold: true
                    Layout.alignment: Qt.AlignVCenter
                }

                Label {
                    text: qsTr("系统参数与显示配置")
                    color: coreStyle.labelColor
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
                        color: closeButton.hovered ? "#C42B1C" : coreStyle.panelElevatedColor
                        radius: coreStyle.controlRadius
                    }

                    contentItem: Text {
                        text: closeButton.text
                        color: closeButton.hovered ? "#FFFFFF" : coreStyle.labelColor
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
                color: coreStyle.panelBackgroundColor
            }

            Repeater {
                model: [
                    qsTr("常规"),
                    qsTr("风格"),
                    qsTr("报警"),
                    qsTr("3D 渲染"),
                    qsTr("相机调整"),
                    qsTr("信息"),
                    qsTr("其他")
                ]

                TabButton {
                    id: tabButton
                    text: modelData
                    font.pixelSize: 14
                    contentItem: Text {
                        text: tabButton.text
                        color: tabButton.checked ? coreStyle.titleColor : coreStyle.labelColor
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font: tabButton.font
                    }
                    background: Rectangle {
                        color: tabButton.checked ? coreStyle.panelElevatedColor : coreStyle.panelBackgroundColor
                        border.color: tabButton.checked ? coreStyle.titleColor : coreStyle.headerBorderColor
                        border.width: tabButton.checked ? 1 : 0
                        radius: coreStyle.controlRadius
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: coreStyle.headerBorderColor
        }

        StackLayout {
            Layout.fillHeight: true
            Layout.fillWidth: true
            currentIndex: tabBar.currentIndex
            clip: true

            GeneralSetting {}
            StyleSetting {}
            AlarmSetting {}
            D3Setting {}
            CameraSetting {}
            InfoSetting {}
            OtherSetting {}
        }
    }
}
