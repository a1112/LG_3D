import QtQuick
// 筛选的 参数类别
import "../../Base"

Item {
    id:root

    readonly property ListModel defectDictModel:defectCoreModel.defectDictModel // 对于缺陷列表的显示



    property bool fliterShowBgDefect:false  // 显示缺陷
    function setFliterShowBgDefect(new_checked){
        fliterShowBgDefect = new_checked
        filterCore.resetFilterDict()
    }

    function  reset(){
        defectCoreModel.initDefectDictModel()
    }

    property var filterDict:{1:1}

    function resetFilterDict(){
        tool.for_list_model(defectDictModel, (item)=>{
                                filterDict[item["name"] ] = item["filter"]
                            })
        let temp= filterDict
        filterDict={}
        filterDict = temp
        defectCoreModel.flushModel()
    }

    function showAll(is_show){
        tool.for_list_model(defectDictModel, (item)=>{
                                if  (!item["show"] && !fliterShowBgDefect)
                                {
                                    item["filter"] =  false
                                }
                                else
                                {
                                    item["filter"] =  is_show
                                }
                            })
        resetFilterDict()
    }

    SettingsBase{
        category : "defect_filter"
        property alias fliterShowBgDefect:root.fliterShowBgDefect
    }
    function nameIsShow(name){
        return filterDict[name]
    }

    function itemIsShow(item){
        console.log(JSON.stringify(filterDict))
        return nameIsShow(item["defectName"])
    }

}
