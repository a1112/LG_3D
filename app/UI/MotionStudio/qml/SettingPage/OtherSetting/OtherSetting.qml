import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout{
    id: root

    required property var apiClient
    required property var style
    required property var settings
    required property var appInfo
    required property var downloadClient

    spacing: 16
    Layout.margins: 20

    SoftwareUpdate{
        apiClient: root.apiClient
        style: root.style
        settings: root.settings
        appInfo: root.appInfo
        downloadClient: root.downloadClient
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
                    checked: root.settings.showTileDebugBorders
                    onCheckedChanged:
                        root.settings.showTileDebugBorders = checked
                }
                Label{
                    text: qsTr("显示 AREA 视图的瓦片调试边框（绿色=已完成，黄色=加载中）")
                    font.pixelSize: 12
                    color: root.style.labelColor
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
                    checked: root.settings.testMode
                    onCheckedChanged: root.settings.testMode = checked
                }
                Label{
                    text: qsTr("启用测试模式后，系统将使用测试数据")
                    font.pixelSize: 12
                    color: root.style.labelColor
                }
            }
        }
    }
}
