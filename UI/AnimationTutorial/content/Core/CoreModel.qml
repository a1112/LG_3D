import QtQuick
import QtQuick.Controls.Material
import "_base_"
import "Surface"
CoreModel_ {

    property CoreGlobalError coreGlobalError:CoreGlobalError{}

    property int maxCoilListModelLen: 300

    property int currentCoilListIndex: 0

    readonly property bool isListRealModel:currentCoilListIndex==0
    readonly property bool isListHistoryModel:currentCoilListIndex==1

    function listToRealModel(){
        currentCoilListIndex=0
    }
    function listToHistoryModel(){
        currentCoilListIndex=1
    }

    function switchListModel(){
        if(isListRealModel){
            listToHistoryModel()
        }
        else{
            listToRealModel()
        }
        }

    readonly property color currentCoilListTextColor: currentCoilListIndex === 0 ? Material.color(Material.Green) : Material.color(Material.Yellow)
    readonly property ListModel historyCoilListModel: ListModel{
    }

    readonly property ListModel coilListModel: ListModel{  // list
    }

    readonly property ListModel realCoilListModel: coilListModel

    readonly property ListModel currentCoilListModel: currentCoilListIndex === 0 ? realCoilListModel : historyCoilListModel
    function getCurrentCoilListModelMinMaxId(){
        return [currentCoilListModel.get(currentCoilListModel.count-1).Id,currentCoilListModel.get(0).Id]
    }
    function getCurrentCoilListModelMinMaxDateTime(){
        return [currentCoilListModel.get(currentCoilListModel.count-1).DateTime,currentCoilListModel.get(0).DateTime]
    }

    function getLastCoilId(){
        return coilListModel.get(0).SecondaryCoilId
    }
    readonly property int lastCoilId: realCoilListModel.get(Math.min(0,realCoilListModel.count)).SecondaryCoilId

    property ListModel surfaceModel: ListModel{
    }

    function setShowMax(key,value){
        if(key === "L"){
            surfaceS.show_visible=!surfaceS.show_visible
        }
        else if(key === "S"){
            surfaceL.show_visible=!surfaceL.show_visible
        }
    }



    property SurfaceData surfaceL: SurfaceData{
        currentCoilModel: core.currentCoilModel
        key:"L"
    }

    property SurfaceData surfaceS: SurfaceData{
        currentCoilModel: core.currentCoilModel
        key:"S"
    }


    property var errorMap: {return {}}
    property var rendererList: []
    property var colorMaps: {return {}}
    property string saveImageType: "png"
    property var previewSize: [512,512]
    function updateData(upData){
        while(coilListModel.count > maxCoilListModelLen){
            coilListModel.remove(coilListModel.count-1,1)
        }
        upData["coilList"].forEach(function(coil){
            if(coil.SecondaryCoilId > lastCoilId){
                realCoilListModel.insert(0,coil)
                // lastCoilId = coil.SecondaryCoilId
            }
            else{
                for (let i = 0;i<20;i++){
                    if (realCoilListModel.get(i).SecondaryCoilId == coil.SecondaryCoilId){
                        realCoilListModel.set(i,coil)
                    }
                }
            }
        })
        if (keepLatest){
        core.setCoilIndex(0)
        }
    }

    // search

    function setSearch(data){

    currentCoilListIndex=1
        historyCoilListModel.clear()
        for(var i=0;i<data.length;i++){
            historyCoilListModel.insert(0,data[i])
        }
        core.setCoilIndex(-1)
        core.setCoilIndex(0)
    }

    function searchByCoilNo(coilNo){
        api.searchByCoilNo(coilNo,
                           (result)=>{
                                setSearch(JSON.parse(result))
                           },
                           (error)=>{}
                           )
    }
    function searchByCoilId(coilId){
        api.searchByCoilId(coilId,
                           (result)=>{
                               setSearch(JSON.parse(result))
                           },
                           (error)=>{}

                           )
    }

    function searchByCoilDateTime(start,end){
        api.searchByTime(start,end,
                           (result)=>{
                                     console.log(result)
                                     setSearch(JSON.parse(result))
                                 },
                           (error)=>{}
        )
    }


}
