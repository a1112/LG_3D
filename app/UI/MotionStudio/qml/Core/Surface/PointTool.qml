import QtQuick
import "../../Model/server"
Item {
    property var pointDatas:[]
    property ListModel pointDbData: ListModel{
        dynamicRoles: true
    }

    property ListModel pointUserData:ListModel{
        dynamicRoles: true
    }

    function clear(){
        pointUserData.clear()
        return pointDbData.clear()
    }

    function addUserPoint(px,py){
        var def= pointDataItem.defaultPoint
        def["p_x"] = px
        def["p_y"] = py
        def["p_z"] = 0
        def["type"]="user"
        // 创建副本，避免修改原始对象，并过滤掉 null 值
        var cleanDef = {}
        for (var key in def) {
            if (def[key] !== null && def[key] !== undefined) {
                cleanDef[key] = def[key]
            }
        }
        pointUserData.append(cleanDef)
    }

    function addDbPoint(dataItem){
        if (!dataItem) return
        if (dataItem["x"] === null || dataItem["x"] === undefined ||
                dataItem["y"] === null || dataItem["y"] === undefined) {
            return
        }
        dataItem["p_x"]=dataItem["x"]
        dataItem["p_y"]=dataItem["y"]
        dataItem["p_z"]=dataItem["z"]
        if (dataItem["z_mm"]<15) return
        // 创建副本，过滤掉 null 值
        var cleanItem = {}
        for (var key in dataItem) {
            if (dataItem[key] !== null && dataItem[key] !== undefined) {
                cleanItem[key] = dataItem[key]
            }
        }
        pointDbData.append(cleanItem)
    }

    property PointData pointDataItem:PointData{}


    function setDatas(data){
        pointDatas=data
        data.forEach((value)=>{
            addDbPoint(value)
                    })

    }
}
