import QtQuick
// 筛选的 参数类别
import "../../Base"

Item {
    id:root

    required property var defectModel
    required property var globalContext
    required property var toolService

    readonly property ListModel defectDictModel: root.defectModel.defectDictModel


    property bool fliterShowBgDefect:false  // 显示缺陷
    function setFliterShowBgDefect(new_checked){
        root.fliterShowBgDefect = new_checked
        root.resetFilterDict()
    }

    function  reset(){
        root.defectModel.initDefectDictModel()
    }

    property var filterDict:{1:1}

    function resetFilterDict(){
        root.toolService.for_list_model(root.defectDictModel, (item)=>{
                                root.filterDict[item["name"] ] = item["filter"]
                            })
        let temp = root.filterDict
        root.filterDict = {}
        root.filterDict = temp
        root.defectModel.flushModel()
    }

    function showAll(is_show){
        root.toolService.for_list_model(root.defectDictModel, (item)=>{
                                if  (!item["show"] && !root.fliterShowBgDefect)
                                {
                                    item["filter"] =  false
                                }
                                else
                                {
                                    item["filter"] =  is_show
                                }
                            })
        root.resetFilterDict()
    }

    SettingsBase{
        category : "defect_filter"
        property alias fliterShowBgDefect:root.fliterShowBgDefect
    }
    function nameIsShow(name){
        let sharedName = root.globalContext.defectClassProperty.shared_defect_name(name)
        return root.filterDict[sharedName]
    }

    function itemIsShow(item){
        // console.log(JSON.stringify(filterDict))
        return nameIsShow(item["configDefectName"] || item["defectName"])
    }

}
