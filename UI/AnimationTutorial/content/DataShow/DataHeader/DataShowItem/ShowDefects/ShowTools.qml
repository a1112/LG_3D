import QtQuick
import QtQuick.Controls
Row {
    spacing:3

    CheckDelegate{
        height:parent.height
        text:"显示屏蔽"
        checked:dataShowCore.defectManage.un_defect_show
        onCheckedChanged:{
            if(dataShowCore.defectManage.un_defect_show!= checked){
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
        text:"取消"
        onClicked: dataShowCore.defectManage.setAllDefectShow(false)

    }
    ItemDelegate{
        text:"全选"
        height:parent.height
        onClicked: dataShowCore.defectManage.setAllDefectShow(true)
    }
}
