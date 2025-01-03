import QtQuick

Item {
    property var defectDictData:{return {}}
    property ListModel defectDictModel:ListModel{
    }


    function getColorByName(name){
        return defectDictData[name].color
    }


    // 记录缺陷显示
    property var defectDictAll: {return {}}
    function flushDefectDictAll(){
    let temp = defectDictAll
        defectDictAll = {}
        defectDictAll = temp
    }


    function setDefectDict(defectData){
        console.log("setDefectDict")
        console.log(JSON.stringify(defectData))
        defectDictData = defectData["data"]
        defectDictModel.clear()
        defectData["data"].forEach((data,index)=>{
                                   defectDictModel.append(data)
                                   })
    }
}
