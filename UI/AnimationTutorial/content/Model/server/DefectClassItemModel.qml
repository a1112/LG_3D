import QtQuick

QtObject {
    property string defectName : name??""
    property int defectLevel: level??0
    property color defectColor:color??""
    property int defectShow:show??false
    property int defectNum:num??0

    function init(itemData){
        if (undefined === itemData){
            return false
        }

        defectName = itemData["name"]
        defectLevel = itemData["level"]
        defectColor = itemData["color"]
        defectShow = itemData["show"]
        defectNum = itemData["num"]
    }
}
