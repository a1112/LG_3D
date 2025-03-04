import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Item {
    id:root
    // width:620
    height:flow.height
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



        Flow{
            id:flow
            spacing:2
            width:parent.width
            // height:parent.height
        Repeater{
            model:root.defectModel
            DefectInfoItem{
            }

        }
        }

}
