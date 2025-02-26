import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Rectangle {
    id:root
    // width:620
    // height:223
    Layout.fillWidth:true
    Layout.fillHeight:true
    property ListModel defectModel:ListModel{}
    property var defectsData:coilModel.defectsData
    onDefectsDataChanged:{
        defectModel.clear()

        tool.for_list_model(defectsData,(defect)=>{
                    defectModel.append(defect)
                            })
    }


    ScrollView{
        width:parent.width
        height:parent.height
        ScrollBar.vertical: ScrollBar{}
        Flow{
            spacing:2
            width:parent.width
            height:parent.height
        Repeater{
            model:root.defectModel
            DefectInfoItem{

            }

        }
        }

    }
}
