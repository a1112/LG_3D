import QtQuick

QtObject {
    property string defectName : name??""
    property int defectLevel: level??0
    property color defectColor:color??""
    property int defectShow:show??false

    function init(itemData){
        defectName = itemData["name"]
        defectLevel = itemData["level"]
        defectColor = itemData["color"]
        defectShow = itemData["show"]
    }
}
