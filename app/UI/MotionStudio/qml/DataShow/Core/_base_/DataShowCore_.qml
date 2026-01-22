import QtQuick
import "../"
import "../../../Core/Surface"
import "../../../DataShow/2dShow/ViewTool"
Item {

    property SurfaceData surfaceData

    property Image image_show

    property Binds binds :Binds{
        surfaceData:surfaceData
    }
    //      alias objcet
    readonly property AdjustConfig adjustConfig:binds.adjustConfig
    readonly property TopDataManage topDataManage :binds.topDataManage
    readonly property DefectManage defectManage:binds.defectManage
    //      end alias
    readonly property bool show_visible:surfaceData.show_visible    // 是否显示
    property CircleConfig circleConfig:CircleConfig{}   // 圆的参数

    property string errorScaleColor:"red"   // 超限制报警色
    property bool errorScaleSignal: false
    function setMaxErrorScale(col){
        errorScaleColor = col
        errorScaleSignal = true
    }

    property Image imageItem



    // 缺陷相关功能

    property var defectDict: {return {}}    // 全部缺陷

    property ListModel defectAllModel: ListModel{}

    // property ListModel has_defectModel: ListModel{}
    // property ListModel un_defectModel: ListModel{}

    property ListModel defectModel: defectAllModel    // defectManage.un_defect_show? defectAllModel : has_defectModel
    property ListModel areaDefectModel: ListModel{} // 2D 缺陷


    property ListModel defecClassListModel:ListModel{}
    // property ListModel currentDefectDictModel:ListModel{ // 缺陷类别
    // }

    // property ListModel currentUnShowDefectDictModel:ListModel{ // 不显示的缺陷类别
    // }

    function getNumByDefectName(defectName){
        if (defectName in defectDict){
            return defectDict[defectName].length
        }
        return 0
    }

    function set_num(){
        var num = 0
        let temp_show_num=0
        for (var defectName_ in defectDict){
            if (!defect_show(defectName_)){
                num += defectDict[defectName_].length
            }
            else{
                temp_show_num += defectDict[defectName_].length
            }

        }

        un_show_num =  num
        show_num = temp_show_num
    }

    property int show_num:0
    property int un_show_num:0

    function defect_show(defectName){
        return global.defectClassProperty.defectDictAll[defectName]??false
    }

    function appendDefect(item){


    }
    function set_show_state(){ // 设置显示状态
        return tool.for_list_model(global.defectClassProperty.defectDictModel,(item)=>{
                                       let name = item.name
                                       if (!(item["name"] in coreModel.defectDictAll)){
                                           coreModel.defectDictAll[item["name"]]=item["show"]
                                       }

                                       // 过滤掉 null 值
                                       let cleanItem = {}
                                       for (let key in item) {
                                           if (item[key] !== null && item[key] !== undefined) {
                                               cleanItem[key] = item[key]
                                           }
                                       }

                                       if (name in defectDict){
                                           defecClassListModel.append(cleanItem)
                                       }
                                   })


    }
    property var defectsData: []

    onDefectsDataChanged: {
        // 刷新全部的缺陷数据
        defectClear()

        if(defectsData.length>0){
            defectsData.forEach((item)=>{
                                    if (!item) return
                                    let defectName = item.defectName
                                    if (defectName in defectDict){
                                        defectDict[defectName].push(item)
                                    }
                                    else{
                                        defectDict[defectName] = [item]
                                    }

                                    // 过滤掉 null 值
                                    let cleanItem = {}
                                    for (let key in item) {
                                        if (item[key] !== null && item[key] !== undefined) {
                                            cleanItem[key] = item[key]
                                        }
                                    }

                                    if(defectName.indexOf("2D_")>=0){
                                        cleanItem["is_area"]=true
                                        cleanItem.defectName=cleanItem.defectName.slice(3)
                                        areaDefectModel.append(cleanItem)
                                    }
                                    else{
                                        cleanItem["is_area"]=false
                                    }
                                    // else{
                                    //     defectAllModel.append(cleanItem)
                                    // }
                                    defectAllModel.append(cleanItem)

                                })
        }
        set_show_state()
        set_num()
    }

    function defectClear(){
        defectAllModel.clear()
        defecClassListModel.clear()
        areaDefectModel.clear()
        defectDict = {}
    }

    function flushDefect(){//刷新
        defectClear()
        api.getDefects(surfaceData.coilId,surfaceData.key,
                       (result)=>{
                           defectsData = JSON.parse(result)
                       },
                       (err)=>{
                       }
                       )
    }



}
