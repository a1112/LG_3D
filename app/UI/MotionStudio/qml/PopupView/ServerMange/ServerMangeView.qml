import QtQuick
import "../Base"

import QtQuick.Layouts
PopupBase {
    width: adaptive.boundedWidth(600, 420, 760)
    height: adaptive.boundedHeight(400, 300, 560)
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
