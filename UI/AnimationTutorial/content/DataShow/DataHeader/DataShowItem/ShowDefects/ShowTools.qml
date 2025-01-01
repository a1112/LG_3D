import QtQuick
import QtQuick.Controls
Row {
    spacing:3

    CheckDelegate{
        height:parent.height
        text:"显示屏蔽"
        checked:dataShowCore.defectManage.un_defect_show
        onClicked:{
            dataShowCore.defectManage.un_defect_show = checked
        }
    }

    ItemDelegate{
        height:parent.height
        text:"取消"
        onClicked: dataShowCore.defectManage.setAllDefectShow(false)

    }
    ItemDelegate{
        text:"全选"
        height:parent.height
        onClicked: dataShowCore.defectManage.setAllDefectShow(true)
    }
}
