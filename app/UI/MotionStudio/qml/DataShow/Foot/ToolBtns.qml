import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../Labels"

RowLayout {
    id: root
    height: parent.height
    spacing: 8

    KeyLabel {
        text: qsTr("工具:")
        Layout.alignment: Qt.AlignVCenter
    }

    ToolPopupButton {
        iconName: "MourceArray"
        popupTitle: qsTr("自由查看")
        popupDescription: qsTr("用于查看图像、定位曲线采样点。双击图像可把当前点设为曲线贯穿方向。")
        selected: dataShowCore.controls.isMoveModel
        onActivateRequested: {
            dataShowCore.controls.currentMouseModel = dataShowCore.controls.mouseMoveModel
        }
    }

    ToolPopupButton {
        iconName: "survey"
        popupTitle: qsTr("测量工具")
        popupDescription: qsTr("用于在图像上选择起点和终点，显示两点距离和水平/垂直偏移。")
        selected: dataShowCore.controls.isShowSurveyModel
        onActivateRequested: {
            dataShowCore.controls.currentMouseModel = dataShowCore.controls.mouseSurveyModel
        }
    }

    component ToolPopupButton: Item {
        id: toolItem

        property string iconName: ""
        property string popupTitle: ""
        property string popupDescription: ""
        property bool selected: false
        signal activateRequested()

        implicitWidth: 25
        implicitHeight: 25
        Layout.preferredWidth: implicitWidth
        Layout.preferredHeight: implicitHeight
        Layout.alignment: Qt.AlignVCenter

        ToolButton {
            id: iconButton
            anchors.fill: parent
            padding: 2
            checkable: true
            checked: toolItem.selected
            ToolTip.visible: hovered
            ToolTip.text: toolItem.popupTitle
            onClicked: {
                toolItem.activateRequested()
                toolPopup.open()
            }

            background: Rectangle {
                color: iconButton.checked ? coreStyle.selectionColor : coreStyle.panelElevatedColor
                border.color: iconButton.checked ? coreStyle.titleColor : coreStyle.headerBorderColor
                border.width: iconButton.checked ? 2 : 1
                radius: coreStyle.controlRadius
            }

            contentItem: Image {
                source: coreStyle.getIcon(toolItem.iconName)
                fillMode: Image.PreserveAspectFit
                mipmap: true
                anchors.margins: 3
            }
        }

        Popup {
            id: toolPopup
            parent: Overlay.overlay
            width: 320
            height: popupLayout.implicitHeight + 26
            modal: false
            focus: true
            padding: 0
            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
            x: Math.max(16, Math.min((parent ? parent.width : 360) - width - 16,
                                     toolItem.mapToItem(parent, 0, 0).x - width / 2 + toolItem.width / 2))
            y: Math.max(54, toolItem.mapToItem(parent, 0, 0).y + toolItem.height + 8)

            background: Rectangle {
                color: coreStyle.panelBackgroundColor
                border.color: coreStyle.headerBorderColor
                border.width: 1
                radius: coreStyle.controlRadius
            }

            ColumnLayout {
                id: popupLayout
                anchors.fill: parent
                anchors.margins: 13
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Rectangle {
                        Layout.preferredWidth: 34
                        Layout.preferredHeight: 34
                        color: toolItem.selected ? coreStyle.selectionColor : coreStyle.panelElevatedColor
                        border.color: toolItem.selected ? coreStyle.titleColor : coreStyle.headerBorderColor
                        border.width: 1
                        radius: coreStyle.controlRadius

                        Image {
                            anchors.fill: parent
                            anchors.margins: 6
                            source: coreStyle.getIcon(toolItem.iconName)
                            fillMode: Image.PreserveAspectFit
                            mipmap: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Label {
                            text: toolItem.popupTitle
                            color: coreStyle.titleColor
                            font.pixelSize: 15
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        Label {
                            text: toolItem.selected ? qsTr("当前已启用") : qsTr("当前未启用")
                            color: toolItem.selected ? coreStyle.titleColor : coreStyle.labelColor
                            font.pixelSize: 12
                            Layout.fillWidth: true
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: coreStyle.headerBorderColor
                }

                Label {
                    text: toolItem.popupDescription
                    color: coreStyle.labelColor
                    font.pixelSize: 13
                    lineHeight: 1.2
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Button {
                        id: activateButton
                        text: toolItem.selected ? qsTr("保持启用") : qsTr("启用工具")
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        onClicked: {
                            toolItem.activateRequested()
                            toolPopup.close()
                        }

                        background: Rectangle {
                            color: toolItem.selected ? coreStyle.selectionColor : coreStyle.panelElevatedColor
                            border.color: coreStyle.titleColor
                            border.width: 1
                            radius: coreStyle.controlRadius
                        }

                        contentItem: Text {
                            text: activateButton.text
                            color: coreStyle.textColor
                            font.pixelSize: 13
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }

                    Button {
                        id: closeButton
                        text: qsTr("关闭")
                        Layout.preferredWidth: 72
                        Layout.preferredHeight: 34
                        onClicked: toolPopup.close()

                        background: Rectangle {
                            color: coreStyle.panelElevatedColor
                            border.color: coreStyle.headerBorderColor
                            border.width: 1
                            radius: coreStyle.controlRadius
                        }

                        contentItem: Text {
                            text: closeButton.text
                            color: coreStyle.labelColor
                            font.pixelSize: 13
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
        }
    }
}
