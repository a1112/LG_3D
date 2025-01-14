import QtQuick
import "../Model/server"
Item {
    id:root
    property var defectDictData:{return {}}
    property ListModel defectDictModel:ListModel{
        // 全部的缺陷类别数据
    }

    property string unDefectClassItemName:"无缺陷"

    property DefectClassItemModel defaultDefectClass:DefectClassItemModel{}   //  默认的缺陷列表
    property DefectClassItemModel unDefectClassItemModel:DefectClassItemModel{
        defectName: root.unDefectClassItemName
        defectLevel:0
        defectColor:coreStyle.labelColor
    }
    function getColorByName(name){
        return defectDictData[name].color
    }


    // 记录缺陷显示
    property var defectDictAll: {return {}}

    property var defecShowTabel:defectDictAll

    function flushDefectDictAll(){
    let temp = defectDictAll
        defectDictAll = {}
        defectDictAll = temp
    }

    function setDefectDict(defectData){
        defectDictData = defectData["data"]
        defectDictModel.clear()
        // 先添加显示的缺陷
        for(let key in defectData["data"]){
            let value = defectData["data"][key]
            value["name"] = key
            value["num"] = 0
            if (value["show"]){
            defectDictModel.append(value)
                }
        }
        // 添加隐藏的缺陷
        for(let key in defectData["data"]){
            let value = defectData["data"][key]
            value["name"] = key
            if (!value["show"]){
            defectDictModel.append(value)
                }
        }
        defaultDefectClass.init(defectData["default"])
    }

    function getDefectLevelByDefectName(defectName){
        return defectDictData[defectName]["level"]??defaultDefectClass.defectLevel
    }
}
