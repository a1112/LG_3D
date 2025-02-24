import QtQuick
import QtQuick.Controls
Item {
    id:root
    height:223

    property ListModel defectModel:ListModel{}
    property var defectsData:coilModel.defectsData
    onDefectsDataChanged:{
        defectModel.clear()

        tool.for_list_model(defectsData,(defect)=>{
                    defectModel.append(defect)
                            })
    }


    ScrollView{
        anchors.fill:parent
        ScrollBar.vertical: ScrollBar{}
        Flow{
            spacing:2
            anchors.fill:parent
        Repeater{
            model:root.defectModel
            DefectInfoItem{

            }

        }
        }

    }
}
