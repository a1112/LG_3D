import QtQuick
import "../Model/server"
import "../Base"
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
        for(let key in defectDictData){
            let value = defectDictData[key]
            value["name"] = key
            value["num"] = 0
            if (value["show"]){
                defectDictModel.append(value)
            }
        }

        for(let key in defectDictData){
            let value = defectDictData[key]
            value["name"] = key
            value["num"] = 0
            if (!value["show"]){
                defectDictModel.append(value)
            }
        }
    }

    function setDefectDict(defectData){
        defectDictData = defectData["data"]
        upDefectDictModelByDefectDictData()
        // defectDictModel.clear()
        // // 先添加显示的缺陷
        // for(let key in defectData["data"]){
        //     let value = defectData["data"][key]
        //     value["name"] = key
        //     value["num"] = 0
        //     if (value["show"]){
        //     defectDictModel.append(value)
        //         }
        // }
        // 添加隐藏的缺陷
        // for(let key in defectData["data"]){
        //     let value = defectData["data"][key]
        //     value["name"] = key
        //     if (!value["show"]){
        //     defectDictModel.append(value)
        //         }
        // }
        defaultDefectClass.init(defectData["default"])
    }

    function getDefectLevelByDefectName(defectName){
        // console.log("defectDictData",JSON.stringify(defectDictData))
        // {"刮丝":{"level":3,"color":"#00007f","show":true,"name":"刮丝","num":0},"边部褶皱":{"level":4,"color":"#aaff00","show":true,"name":"边部褶皱","num":0},"背景_塔形":{"level":1,"color":"#FFA500","show":false,"name":"背景_塔形","num":0},"背景_头尾":{"level":1,"color":"#FFA500","show":false,"name":"背景_头尾","num":0},"小型缺陷":{"level":2,"color":"#FFA500","show":true,"name":"小型缺陷","num":0},"背景_打包带":{"level":1,"color":"#FFA500","show":false,"name":"背景_打包带","num":0},"折叠":{"level":5,"color":"#FFA500","show":true,"name":"折叠","num":0},"背景_数据脏污":{"level":1,"color":"#FFA500","show":false,"name":"背景_数据脏污","num":0},"毛刺":{"level":3,"color":"#FFA500","show":true,"name":"毛刺","num":0},"背景":{"level":0,"color":"#FFFFFF","show":false,"name":"背景","num":0},"烂边":{"level":5,"color":"#aa00ff","show":true,"name":"烂边","num":0},"分层":{"level":5,"color":"red","show":true,"name":"分层","num":0},"脏污":{"level":1,"color":"#FFA500","show":false,"name":"脏污","num":0},"背景_边部":{"level":1,"color":"#FFA500","show":false,"name":"背景_边部","num":0}}
        if(defectName in defectDictData){
            return defectDictData[defectName]["level"]??defaultDefectClass.defectLevel
        }
        return 1
    }
    function getColorByName(name){
        return defectDictData[name]["color"]
    }
    property bool defeftDrawShowLasbel:true


    SettingsBase{
        property alias defeftDrawShowLasbel:root.defeftDrawShowLasbel

    }



    function selecct_all_un_defect_show(){
        console.log("selecct_all_un_defect_show")
        for(let key in defectDictData){
            let value = defectDictData[key]
            if(!value["show"]){
            defectDictAll[value["name"]]=true
            }
        }
        coreModel.flushDefectDictAll()
    }

    function un_selecct_all_un_defect_show(){
        for(let key in defectDictData){
            let value = defectDictData[key]
            if(!value["show"]){
            defectDictAll[value["name"]]=false
                }
        }
        coreModel.flushDefectDictAll()
    }
}
