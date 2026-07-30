pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
Item {
    id:root
    // width:620
    height:flow.height
    Layout.fillWidth:true
    Layout.fillHeight:true
    property var coilModel
    visible: coilModel !== undefined
    property bool respectFilter: false
    property int thumbnailSize: 96
    required property var toolService
    required property var filterController
    required property var globalContext
    required property var apiClient
    property ListModel defectModel:ListModel{}
    property var defectsData:coilModel ? coilModel.defectsData : null
    onDefectsDataChanged:{
        defectModel.clear()
        if (defectsData) {
            root.toolService.for_list_model(root.defectsData,(defect)=>{
                        root.defectModel.append(defect)
                                })
        }
    }



        Flow{
            id:flow
            spacing:2
            width:parent.width
            // height:parent.height
        Repeater{
            model:root.defectModel
            DefectInfoItem{
                defectData: root.defectModel.get(index)
                respectFilter: root.respectFilter
                thumbnailSize: root.thumbnailSize
                filterController: root.filterController
                globalContext: root.globalContext
                apiClient: root.apiClient
            }

        }
        }

}
