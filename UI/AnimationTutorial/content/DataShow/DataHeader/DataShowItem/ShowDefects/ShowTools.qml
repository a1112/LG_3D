import QtQuick
import QtQuick.Controls
Row {
    spacing:2


    CheckDelegate{
        height:parent.height
        text:"2D类"
        checked: dataShowCore.defectManage.area_defect_show
        onCheckedChanged:{
            if(dataShowCore.defectManage.area_defect_show !== checked){
                if (checked){
                    global.defectClassProperty.select_area_defect()
                }
                else{
                    global.defectClassProperty.un_select_area_defect()
                }
            }
        }
        onClicked:{
            dataShowCore.defectManage.area_defect_show = checked
        }
    }

    CheckDelegate{
        height:parent.height
        text:"屏蔽类"
        checked: dataShowCore.defectManage.un_defect_show
        onCheckedChanged:{
            if(dataShowCore.defectManage.un_defect_show !== checked){
                if (checked){
                    global.defectClassProperty.selecct_all_un_defect_show()
                }
                else{
                    global.defectClassProperty.un_selecct_all_un_defect_show()
                }
            }
        }
        onClicked:{
            dataShowCore.defectManage.un_defect_show = checked
        }
    }


    DefectNumLabel{
        defect_num:dataShowCore.un_show_num
    }
    ItemDelegate{
        height:parent.height
        text:qsTr("取消")
        onClicked: dataShowCore.defectManage.setAllDefectShow(false)

    }
    ItemDelegate{
        text:qsTr("全选")
        height:parent.height
        onClicked: dataShowCore.defectManage.setAllDefectShow(true)
    }
}
