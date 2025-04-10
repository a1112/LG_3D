import QtQuick

QtObject {
    property string defectName : name ?? ""
    property int defectLevel: level ?? 0
    property color defectColor:color ?? ""
    property bool defectShow:show ??  false
    property int defectNum:num ?? 0
    property bool filterShow:filter ??  true

    property var data

    function init(itemData){
        data = itemData
        if (undefined === itemData){
            return false
        }

        defectName = itemData["name"]
        defectLevel = itemData["level"]
        defectColor = itemData["color"]
        defectShow = itemData["show"]
        defectNum = itemData["num"]
    }




    function itemTodict(item){
        return {
            "name": item["name"],
            "level": item["level"],
            "color": item["color"],
            "show": item["show"],
            "num": item["num"],
            "filter" : item["show"],
        }

    }
}
