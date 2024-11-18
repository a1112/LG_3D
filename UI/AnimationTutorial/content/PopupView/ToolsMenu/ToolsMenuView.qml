import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

Menu {


        MenuItem{
            text:qsTr("退出系统")
            onClicked:Qt.quit()
        }

        Menu{
            title:qsTr("维护")
            MenuItem{
                text:"远程到服务器"
                onClicked:{


                }
            }
        }
}
