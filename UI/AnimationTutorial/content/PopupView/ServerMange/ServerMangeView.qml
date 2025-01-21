import QtQuick
import "../Base"

import QtQuick.Layouts
PopupBase {
    width:600
    height:400
    anchors.centerIn:parent
    ColumnLayout{
        width:parent.width
        height:parent.height
        TitleLabel{
            text:"远程服务管理"

        }
        Item{
            Layout.fillWidth:true
            Layout.fillHeight:true
        ListView{


        }
        }

    }

    Timer{


    }

}
