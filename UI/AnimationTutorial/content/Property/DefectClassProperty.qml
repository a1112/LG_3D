import QtQuick

Item {

    property ListModel defectClassModel:ListModel{

    }

    function getColorByName(name){
        return "#0F0"
    }


    // 记录缺陷显示
    property var defectDictAll: {return {}}
    function flushDefectDictAll(){
    let temp = defectDictAll
        defectDictAll = {}
        defectDictAll = temp
    }
}
