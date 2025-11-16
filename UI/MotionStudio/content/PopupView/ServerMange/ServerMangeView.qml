import QtQuick
import "../Base"

import QtQuick.Layouts
PopupBase {
    width:600
    height:400
    anchors.centerIn:parent
    Item{
        anchors.fill:parent
        ColumnLayout{
        anchors.fill:parent
            TitleLabel{
                text:"远程服务管理"
                Layout.alignment: Qt.AlignHCenter
            }
            Item{
                Layout.fillWidth:true
                Layout.fillHeight:true
                ListView{
                }
            }
        }


    }
    Timer{
        id:timert_id

    }
}
