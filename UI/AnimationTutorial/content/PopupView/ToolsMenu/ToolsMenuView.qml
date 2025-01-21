import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

Menu {

    Menu{
        title:qsTr("维护")
        MenuItem{
            text:"远程到服务器"
            onClicked:{
                ScriptLauncher.launchScript("/c start /wait mstsc /v "+api.apiConfig.hostname)
            }
        }
        MenuItem{
            text:"Ping 服务器"
            onClicked:{
                ScriptLauncher.launchScript("/c start /wait ping "+api.apiConfig.hostname+" -t")
            }
        }
        MenuItem{
            text:"一键恢复"
            onClicked:{}
        }

        MenuItem{
            text:"重启全部服务"
            onClicked:{
            }
        }
        MenuItem{
            text:"服务管理"
            onClicked:{
                popManage.popupServerMangeView()

            }
        }
        MenuItem{
            text:"重启服务器"
            onClicked:{


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
                    dialogs.save_sql(
                                (save_file)=>{
                                    api.save_to_sql(save_file,()=>{
                                                        Qt.openUrlExternally(save_file)
                                                    },()=>{
                                                    })
                                }
                                )
                }
            }
            MenuItem{
                text:"从 备份 恢复"
            }
        }

        Menu{
            title:"测试"
            MenuItem{
                text:"网络测速"
            }
        }
    }
    MenuItem{
        text:qsTr("退出系统")
        onClicked:Qt.quit()
    }


}
