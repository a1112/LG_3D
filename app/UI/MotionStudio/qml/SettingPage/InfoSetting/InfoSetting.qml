import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../BaseSetting"

ColumnLayout{
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
                    text: core.developer_mode ? "TestData/125143" : (app.coreSetting.useSharedFolder ? "\\\\" + app.api.apiConfig.hostname + "/" + app.coreSetting.sharedFolderBaseName : "数据库")
                    font.pixelSize: 13
                    color: "#333333"
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
                    text: core.developer_mode ? "TestData (测试数据)" : (app.coreSetting.useSharedFolder ? "共享文件夹" : "本地数据库")
                    font.pixelSize: 13
                    color: "#333333"
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
                    color: core.developer_mode ? "#FF6B6B" : "#51CF66"
                    radius: 4
                    Label{
                        anchors.centerIn: parent
                        text: core.developer_mode ? qsTr("测试模式") : qsTr("生产模式")
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
                    text: app.api.apiConfig.hostname
                    font.pixelSize: 13
                    color: "#333333"
                }
            }
            
            // 数据库状态
            RowLayout{
                spacing: 8
                Label{
                    text: qsTr("数据库：")
                    font.pixelSize: 14
                    font.bold: true
                }
                Label{
                    text: "Offline"
                    font.pixelSize: 13
                    color: "#666666"
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
            
            // 配置文件路径
            RowLayout{
                spacing: 8
                Label{
                    text: qsTr("配置目录：")
                    font.pixelSize: 14
                    font.bold: true
                }
                Label{
                    text: "D:\\CONFIG_3D"
                    font.pixelSize: 13
                    color: "#333333"
                }
            }
            
            // API端口
            RowLayout{
                spacing: 8
                Label{
                    text: qsTr("API端口：")
                    font.pixelSize: 14
                    font.bold: true
                }
                Label{
                    text: app.coreSetting.server_port.toString()
                    font.pixelSize: 13
                    color: "#333333"
                }
            }
        }
    }
    
    // 刷新按钮
    RowLayout{
        Layout.alignment: Qt.AlignRight
        Button{
            text: qsTr("刷新信息")
            onClicked: {
                // 这里可以添加刷新逻辑，重新获取系统信息
                console.log("刷新系统信息")
            }
        }
    }
}