import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout{
    id: root
    required property var apiClient
    required property var settings
    required property var style
    required property var coreController

    spacing: 16
    Layout.margins: 20
    
    GroupBox{
        title: qsTr("系统信息")
        Layout.fillWidth: true
        
        ColumnLayout{
            anchors.fill: parent
            spacing: 12
            
            // 数据源目录
            RowLayout{
                spacing: 8
                Label{
                    text: qsTr("数据源目录：")
                    font.pixelSize: 14
                    font.bold: true
                }
                Label{
                    text: root.coreController.developer_mode
                          ? "TestData/125143"
                          : (root.settings.useSharedFolder
                             ? "\\\\" + root.apiClient.apiConfig.hostname + "/"
                               + root.settings.sharedFolderBaseName
                             : qsTr("数据库"))
                    font.pixelSize: 13
                    color: root.style.secondaryTextColor
                }
            }
            
            // 存储目录
            RowLayout{
                spacing: 8
                Label{
                    text: qsTr("存储目录：")
                    font.pixelSize: 14
                    font.bold: true
                }
                Label{
                    text: root.coreController.developer_mode
                          ? qsTr("TestData（测试数据）")
                          : (root.settings.useSharedFolder ? qsTr("共享文件夹") : qsTr("本地数据库"))
                    font.pixelSize: 13
                    color: root.style.secondaryTextColor
                }
            }
            
            // 运行模式
            RowLayout{
                spacing: 8
                Label{
                    text: qsTr("运行模式：")
                    font.pixelSize: 14
                    font.bold: true
                }
                Rectangle{
                    width: 80
                    height: 24
                    color: root.coreController.developer_mode
                           ? root.style.statusWarningColor : root.style.statusSuccessColor
                    radius: 4
                    Label{
                        anchors.centerIn: parent
                        text: root.coreController.developer_mode ? qsTr("测试模式") : qsTr("生产模式")
                        font.pixelSize: 12
                        color: "white"
                    }
                }
            }
            
            // 主机信息
            RowLayout{
                spacing: 8
                Label{
                    text: qsTr("主机名：")
                    font.pixelSize: 14
                    font.bold: true
                }
                Label{
                    text: root.apiClient.apiConfig.hostname
                    font.pixelSize: 13
                    color: root.style.secondaryTextColor
                }
            }
        }
    }
    
    GroupBox{
        title: qsTr("配置信息")
        Layout.fillWidth: true
        
        ColumnLayout{
            anchors.fill: parent
            spacing: 8
            
            // 图像服务实现
            RowLayout{
                spacing: 8
                Label{
                    text: qsTr("图像服务：")
                    font.pixelSize: 14
                    font.bold: true
                }
                Label{
                    text: root.settings.useRustTestServer ? qsTr("Rust 测试服务") : qsTr("Python 服务")
                    font.pixelSize: 13
                    color: root.style.secondaryTextColor
                }
            }
        }
    }
}
