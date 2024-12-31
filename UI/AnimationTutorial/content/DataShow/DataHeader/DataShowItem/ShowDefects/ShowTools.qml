import QtQuick
import QtQuick.Controls
Row {
    spacing:3

    CheckDelegate{
        height:parent.height
        text:"显示屏蔽"
        checked:dataShowCore.un_defect_show
        onClicked:{
            dataShowCore.un_defect_show = checked
        }
    }

    ItemDelegate{
        height:parent.height
        text:"取消"
    }
    ItemDelegate{
        text:"全选"
        height:parent.height
    }
}
