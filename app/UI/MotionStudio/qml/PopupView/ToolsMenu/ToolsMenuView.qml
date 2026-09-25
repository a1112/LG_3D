import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

Menu {
    id: root

    required property var apiClient
    required property var scriptLauncher
    required property var popupManager
    required property var dialogManager

    Menu{
        title:qsTr("维护")
        MenuItem{
            text:qsTr("远程到服务器")
            onClicked:{
                root.scriptLauncher.launchScript(
                            "/c start /wait mstsc /v "
                            + root.apiClient.apiConfig.hostname)
            }
        }
        MenuItem{
            text:qsTr("Ping 服务器")
            onClicked:{
                root.scriptLauncher.launchScript(
                            "/c start /wait ping "
                            + root.apiClient.apiConfig.hostname + " -t")
            }
        }

    }
    Menu{
        title: "功能"
        Menu{
            title: "数据库备份"
            MenuItem{
                text:"备份到 ..."
                onClicked: {
                    root.dialogManager.save_sql(
                                (save_file)=>{
                                    root.apiClient.save_to_sql(save_file,()=>{
                                                        Qt.openUrlExternally(save_file)
                                                    },()=>{
                                                    })
                                }
                                )
                }
            }
        }
    }
    MenuItem{
        text:qsTr("退出系统")
        onClicked:Qt.quit()
    }


}
