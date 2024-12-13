import QtQuick
Item {
    property var pointDatas:[]
    property ListModel pointData: ListModel{
    }

    function clear(){
        return pointData.clear()
    }
    function addUserPoint(px,py){
        var def= defaultPoint
        def["p_x"] = px
        def["p_y"] = py
        def["type"]="user"
        pointData.append(def)

    }

    function addDbPoint(dataItem){
        dataItem["p_x"]=dataItem["x"]
        dataItem["p_y"]=dataItem["y"]

        if (dataItem["z_mm"]>-15 && dataItem["z_mm"]<15) return
        pointData.append(dataItem)
    }


    property var defaultPoint: {
        "type": "user",
        "secondaryCoilId": 35858,
        "Id": 337249,
        "x": 4012,
        "y": 2891,
        "z_mm": -39.1953,
        "crateTime": {
            "year": 2024,
            "month": 12,
            "weekday": 4,
            "day": 13,
            "hour": 14,
            "minute": 39,
            "second": 15
        },
        "surface": "L",
        "z": 30435,
        "data": null
    }

    function setDatas(data){
        pointDatas=data
        data.forEach((value)=>{
            addDbPoint(value)
                    })

    }
}
