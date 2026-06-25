import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout{
    spacing: 16
    Layout.margins: 20

    SoftwareUpdate{}

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
                    color: coreStyle.labelColor
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
                    color: coreStyle.labelColor
                }
            }
        }
    }
}
