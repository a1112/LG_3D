import QtQuick
import "../"
import "../../../Core/Surface"
import "../../../DataShow/2dShow/ViewTool"
Item {

    property SurfaceData surfaceData

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

    property ListModel defectModel:defectAllModel// defectManage.un_defect_show? defectAllModel : has_defectModel

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
    property var defectsData: []
    onDefectsDataChanged: {

        if(defectsData.length>0){
            defectsData.forEach((item)=>{
                                    let defectName = item.defectName
                                    if (defectName in defectDict){
                                        defectDict[defectName].push(item)
                                    }
                                    else{
                                        defectDict[defectName] = [item]
                                    }

                                    defectAllModel.append(item)
                                 })
            }
            tool.for_list_model(global.defectClassProperty.defectDictModel,(item)=>{
                let name = item.name
                if (!(item["name"] in coreModel.defectDictAll)){
                    coreModel.defectDictAll[item["name"]]=item["show"]
                    }

                if (name in defectDict){
                                    defecClassListModel.append(item)
                                    }
                                })
        set_num()
    }

    function defectClear(){
        defectAllModel.clear()
        defecClassListModel.clear()
        defectDict = {}
    }

    function flushDefect(){
        defectClear()
        api.getDefects(surfaceData.coilId,surfaceData.key,
                       (result)=>{
                           defectsData = JSON.parse(result)
                       },
                       (err)=>{
                       }
                       )
    }

    property View2DTool view2DTool:View2DTool{}

}
