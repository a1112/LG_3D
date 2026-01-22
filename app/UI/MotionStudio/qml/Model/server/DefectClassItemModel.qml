import QtQuick

QtObject {
    property string defectName : ""
    property int defectLevel: 0
    property color defectColor: "#00000000"
    property bool defectShow: false
    property int defectNum: 0
    property bool filterShow: true

    property var data

    function init(itemData){
        data = itemData
        if (undefined === itemData){
            return false
        }

        defectName = itemData["name"] || ""
        defectLevel = itemData["level"] || 0
        defectColor = itemData["color"] || "#00000000"
        defectShow = itemData["show"] || false
        defectNum = itemData["num"] || 0
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
