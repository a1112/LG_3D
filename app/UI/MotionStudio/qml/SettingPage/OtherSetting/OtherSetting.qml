import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../BaseSetting"

ColumnLayout{
    spacing: 16
    Layout.margins: 20

    // ========== 主题选择 ==========
    GroupBox{
        title: qsTr("主题设置")
        Layout.fillWidth: true

        ColumnLayout{
            anchors.fill: parent
            spacing: 12

            Label{
                text: qsTr("选择界面主题")
                font.pixelSize: 16
                font.bold: true
            }

            RowLayout{
                spacing: 12

                Repeater{
                    model: ["dark", "light", "ocean", "forest", "purple", "sunset"]
                    Button{
                        property string themeKey: modelData
                        property string themeDisplayName: coreStyle.themes[modelData].name

                        text: themeDisplayName
                        checked: coreStyle.themeName === themeKey
                        checkable: true
                        autoExclusive: true

                        Layout.preferredWidth: 100
                        Layout.preferredHeight: 40

                        background: Rectangle {
                            color: {
                                if (coreStyle.themeName === parent.themeKey) {
                                    switch(parent.themeKey) {
                                        case "dark": return "#2f2f2f"
                                        case "light": return "#e2e2e2"
                                        case "ocean": return "#1a3a5c"
                                        case "forest": return "#1a3a1a"
                                        case "purple": return "#3a1a5c"
                                        case "sunset": return "#3a2a1a"
                                        default: return "#2f2f2f"
                                    }
                                }
                                return "transparent"
                            }
                            border.color: coreStyle.themeName === parent.themeKey ? coreStyle.titleColor : "#666666"
                            border.width: 2
                            radius: 4

                            Behavior on color { ColorAnimation { duration: 150 } }
                        }

                        contentItem: Text {
                            text: parent.text
                            font.pixelSize: 12
                            color: coreStyle.textColor
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }

                        onClicked: {
                            coreStyle.applyTheme(themeKey)
                        }

                        ToolTip.visible: hovered
                        ToolTip.text: themeDisplayName
                    }
                }
            }

            // 主题预览
            Rectangle{
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                color: coreStyle.isDark ? "#1a1a1a" : "#e0e0e0"
                border.color: coreStyle.titleColor
                border.width: 1
                radius: 4

                Row{
                    anchors.centerIn: parent
                    spacing: 20

                    Rectangle{
                        width: 60
                        height: 20
                        color: coreStyle.titleColor
                        radius: 2
                    }

                    Rectangle{
                        width: 60
                        height: 20
                        color: coreStyle.cardBorderColor
                        radius: 2
                    }

                    Text{
                        text: "主题预览 " + coreStyle.themes[coreStyle.themeName].name
                        color: coreStyle.textColor
                        font.pixelSize: 12
                    }
                }
            }
        }
    }

    // ========== 调试选项 ==========
    GroupBox{
        title: qsTr("调试选项")
        Layout.fillWidth: true

        ColumnLayout{
            anchors.fill: parent
            spacing: 12

            RowLayout{
                spacing: 8
                Label{
                    text: qsTr("显示瓦片边框")
                    font.pixelSize: 16
                }
                Switch{
                    id: tileDebugSwitch
                    checked: coreSetting.showTileDebugBorders
                    onCheckedChanged: coreSetting.showTileDebugBorders = checked
                }
                Label{
                    text: qsTr("显示 AREA 视图的瓦片调试边框（绿色=已完成，黄色=加载中）")
                    font.pixelSize: 12
                    color: "#666666"
                }
            }
        }
    }

    // ========== 系统设置 ==========
    GroupBox{
        title: qsTr("系统设置")
        Layout.fillWidth: true

        ColumnLayout{
            anchors.fill: parent
            spacing: 12

            RowLayout{
                spacing: 8
                Label{
                    text: qsTr("测试模式")
                    font.pixelSize: 16
                }
                Switch{
                    id: testModeSwitch
                    checked: coreSetting.testMode
                    onCheckedChanged: coreSetting.testMode = checked
                }
                Label{
                    text: qsTr("启用测试模式后，系统将使用测试数据")
                    font.pixelSize: 12
                    color: "#666666"
                }
            }
        }
    }
}
