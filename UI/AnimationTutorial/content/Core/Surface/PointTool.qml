import QtQuick
import "../../Model/server"
Item {
    property var pointDatas:[]
    property ListModel pointDbData: ListModel{
    }

    property ListModel pointUserData:ListModel{
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
        pointUserData.append(def)
    }

    function addDbPoint(dataItem){
        dataItem["p_x"]=dataItem["x"]
        dataItem["p_y"]=dataItem["y"]
        dataItem["p_z"]=dataItem["z"]
        if (dataItem["z_mm"]<15) return
        // if (dataItem["z_mm"]>-15 && dataItem["z_mm"]<15) return
        pointDbData.append(dataItem)
    }

    property PointData pointDataItem:PointData{}


    function setDatas(data){
        pointDatas=data
        data.forEach((value)=>{
            addDbPoint(value)
                    })

    }
}
