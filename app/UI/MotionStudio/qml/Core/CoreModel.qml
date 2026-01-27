import QtQuick
import QtQuick.Controls.Material
import "_base_"
import "Surface"
CoreModel_ {

    property CoreGlobalError coreGlobalError:CoreGlobalError{}

    property int maxCoilListModelLen: 300

    property int currentCoilListIndex: 0
    onCurrentCoilListIndexChanged:{
        core.flushListItem()
    }


    readonly property bool isListRealModel:currentCoilListIndex===0
    readonly property bool isListHistoryModel:currentCoilListIndex===1

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

    function insertCoilData(model,data){
        if (model.count>0){

        }

    }

    function getCurrentCoilListModelMinMaxId(){
        if (currentCoilListModel.count === 0) return [0, 0]
        return [currentCoilListModel.get(currentCoilListModel.count-1).Id,currentCoilListModel.get(0).Id]
    }
    function getCurrentCoilListModelMinMaxDateTime(){
        if (currentCoilListModel.count === 0) return [null, null]
        return [currentCoilListModel.get(currentCoilListModel.count-1).DateTime,currentCoilListModel.get(0).DateTime]
    }
    readonly property int lastCoilId: realCoilListModel.count > 0 ? realCoilListModel.get(0).Id || 0 : 0

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

    function getMaxCoilId(){
        return getLastCoilId()
    }

    function getMinCoilId(){
        return realCoilListModel.get(realCoilListModel.count-1).Id
    }

    function getLastCoilId(){
        let max_i=0
        if (realCoilListModel.count===0){

        }
        for(let i =0;i<5;i++){
            let id_ = realCoilListModel.get(0).Id
            if (id_>max_i){
                max_i=id_
            }
        }
        return max_i
    }

    function updateData(upData){
        // 如果正在加载初始数据，跳过更新（防止竞态条件）
        if (app && app.init && app.init.isListLoading) {
            console.log("List is loading, skipping updateData")
            return
        }

        while(coilListModel.count > maxCoilListModelLen){
            coilListModel.remove(coilListModel.count-1,1)
        }

        if (upData["coilList"] === undefined){
            return -2
        }

        // 收集已存在的 ID，避免重复插入
        var existingIds = {}
        for (let i = 0; i < realCoilListModel.count; i++) {
            existingIds[realCoilListModel.get(i).Id] = i
        }

        upData["coilList"].forEach(
                (coil)=>{
                    var coilId = coil.Id
                    // 检查是否已存在
                    if (existingIds[coilId] !== undefined) {
                        // 已存在，更新数据
                        realCoilListModel.set(existingIds[coilId], coil)
                    } else {
                        // 不存在，插入到列表开头（新数据）
                        realCoilListModel.insert(0, coil)
                        existingIds[coilId] = 0
                    }
                }
            )
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
        // core.setCoilIndex(1)
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
                                     // console.log(result)
                                     setSearch(JSON.parse(result))
                                 },
                           (error)=>{}
        )
    }

    property var exportTypeList:["3D检测数据","缺陷数据","全部检测数据"]
    function getExportKeyByName(name){
        return ["3D","2D","ALL"][exportTypeList.indexOf(name)]
    }

    property var has_data // 是否数据存在

    // 待定位的缺陷（从缺陷页面跳转时设置）
    property var pendingDefect: null

}
