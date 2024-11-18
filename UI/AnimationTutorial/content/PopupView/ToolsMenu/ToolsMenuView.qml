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
            text:"一键恢复"
            onClicked:{}
        }

        MenuItem{
            text:"重启全部服务"
            onClicked:{
            }
        }

        MenuItem{
            text:"重启服务器"
            onClicked:{
            }
        }
    }
        MenuItem{
            text:qsTr("退出系统")
            onClicked:Qt.quit()
        }


}
