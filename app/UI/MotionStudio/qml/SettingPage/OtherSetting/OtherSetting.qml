import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../BaseSetting"

ColumnLayout{
    spacing: 16
    Layout.margins: 20
    
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
