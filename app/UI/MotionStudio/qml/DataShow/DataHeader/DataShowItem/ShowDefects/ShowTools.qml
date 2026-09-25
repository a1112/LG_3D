import QtQuick
import QtQuick.Controls
Row {
    id: root

    required property var controller
    required property var defectClassController

    spacing:2


    CheckDelegate{
        height:parent.height
        text:"2D类"
        checked: root.controller.defectManage.area_defect_show
        onCheckedChanged:{
            if(root.controller.defectManage.area_defect_show !== checked){
                if (checked){
                    root.defectClassController.select_area_defect()
                }
                else{
                    root.defectClassController.un_select_area_defect()
                }
            }
        }
        onClicked:{
            root.controller.defectManage.area_defect_show = checked
        }
    }

    CheckDelegate{
        height:parent.height
        text:qsTr("屏蔽类")
        checked: root.controller.defectManage.un_defect_show
        onCheckedChanged:{
            if(root.controller.defectManage.un_defect_show !== checked){
                if (checked){
                    root.defectClassController.selecct_all_un_defect_show()
                }
                else{
                    root.defectClassController.un_selecct_all_un_defect_show()
                }
            }
        }
        onClicked:{
            root.controller.defectManage.un_defect_show = checked
        }
    }


    DefectNumLabel{
        defect_num: root.controller.un_show_num
    }
    ItemDelegate{
        height:parent.height
        text:qsTr("取消")
        onClicked: root.controller.defectManage.setAllDefectShow(false)

    }
    ItemDelegate{
        text:qsTr("全选")
        height:parent.height
        onClicked: root.controller.defectManage.setAllDefectShow(true)
    }
}
