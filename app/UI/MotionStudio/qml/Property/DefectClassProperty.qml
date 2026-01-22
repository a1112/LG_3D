import QtQuick
import "../Model/server"
import "../Base"
Item {
    id:root
    property var defectDictData:{return {}}
    property ListModel defectDictModel : ListModel{
        // 全部的缺陷类别数据
    }

    property string unDefectClassItemName:qsTr("无缺陷")

    property DefectClassItemModel defaultDefectClass:DefectClassItemModel{}   //  默认的缺陷列表
    property DefectClassItemModel unDefectClassItemModel:DefectClassItemModel{
        defectName: root.unDefectClassItemName
        defectLevel:0
        defectColor:coreStyle.labelColor
    }



    // 记录缺陷显示
    property var defectDictAll: {return {}}

    property var defecShowTabel:defectDictAll

    function flushDefectDictAll(){
        let temp = defectDictAll
        defectDictAll = {}
        defectDictAll = temp
    }

    function upDefectDictModelByDefectDictData(){
        defectDictModel.clear()
        // 第一次循环：显示的缺陷
        for(let key in defectDictData){
            let value = defectDictData[key]
            // 创建副本避免修改原始数据
            let item = {}
            item["name"] = key
            item["num"] = 0
            item["level"] = value["level"]
            item["color"] = value["color"]
            item["show"] = value["show"]
            if (value["show"]){
                defectDictModel.append(item)
            }
        }

        // 第二次循环：不显示的缺陷
        for(let key in defectDictData){
            let value = defectDictData[key]
            // 创建副本避免修改原始数据
            let item = {}
            item["name"] = key
            item["num"] = 0
            item["level"] = value["level"]
            item["color"] = value["color"]
            item["show"] = value["show"]
            if (!value["show"]){
                defectDictModel.append(item)
            }
        }
    }

    function setDefectDict(defectData){
        defectDictData = defectData["data"]
        upDefectDictModelByDefectDictData()
        defaultDefectClass.init(defectData["default"])
    }

    function getDefectLevelByDefectName(defectName){
        if(defectName in defectDictData){
            return defectDictData[defectName]["level"]??defaultDefectClass.defectLevel
        }
        return 1
    }
    function getColorByName(name){
        if (defectDictData[name] === undefined){
            return "#FFF"
        }
        return defectDictData[name]["color"]
    }

    function getColorByLevel(level){
        if (level>=3){
            return "red"
        }
        if (level>=2){
            return "yellow"
        }
        if (level>=1){
            return "gray"
        }
        return "#00000000"
    }

    property bool defeftDrawShowLasbel:true


    SettingsBase{
        property alias defeftDrawShowLasbel:root.defeftDrawShowLasbel

    }

    function selecct_all_un_defect_show(){
        // 设置显示 屏蔽的缺陷
        for(let key in defectDictData){
            let value = defectDictData[key]
            if(!value["show"]){
            defectDictAll[value["name"]]=true
            }
        }
        coreModel.flushDefectDictAll()
    }

    function un_selecct_all_un_defect_show(){
        // 设置不显示屏蔽的缺陷
        for(let key in defectDictData){
            let value = defectDictData[key]
            if(!value["show"]){
            defectDictAll[value["name"]]=false
                }
        }
        coreModel.flushDefectDictAll()
    }

    function select_area_defect(){
        // 显示2D类别缺陷
        // for(let key in defectDictData){
        //     let value = defectDictData[key]
        //     if(!value["area"]){
        //     defectDictAll[value["name"]]=false
        //         }
        // }
        // coreModel.flushDefectDictAll()
    }

    function un_select_area_defect(){
        // 不显示2D类别缺陷
        // for(let key in defectDictData){
        //     let value = defectDictData[key]
        //     if(!value["area"]){
        //     defectDictAll[value["name"]]=false
        //         }
        // }
        // coreModel.flushDefectDictAll()
    }
}
