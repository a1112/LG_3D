import QtQuick
import "../"
import "../../../Core/Surface"
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
    property var unShowDefectList: ["塔形", "头尾", "背景","数据脏污"]

    property ListModel defectModel: ListModel{
    }
    property ListModel un_defectModel: ListModel{
    }

    property ListModel currentDefectDictModel:ListModel{ // 缺陷类别
    }
    property ListModel currentUnShowDefectDictModel:ListModel{ // 不显示的缺陷类别
    }

    property var defectsData: []
    onDefectsDataChanged: {
        if(defectsData.length>0){
            for (let i = 0; i < defectsData.length; i++) {
                let item = defectsData[i]

                // console.log(JSON.stringify(item))
                let defectName = item.defectName
                let cddm=currentDefectDictModel
                let dm = defectModel
                if (unShowDefectList.indexOf(defectName)>=0){
                    cddm = currentUnShowDefectDictModel
                    dm = un_defectModel
                }
                if (defectName in defectDict){
                    defectDict[defectName].push(item)
                    for (let j = 0; j < cddm.count; j++) {
                        if (cddm.get(j).defectName == defectName){
                            cddm.setProperty(j,"num",cddm.get(j).num+1)
                        }
                    }
                }
                else{
                    defectDict[defectName] = [item]
                    cddm.append({"defectName":defectName,
                                      "num":1
                                  })
                    if (!(defectName in coreModel.defectDictAll))
                        coreModel.defectDictAll[defectName]=true
                }
                dm.append(defectsData[i])
            }
        }
    }

    function defectClear(){
        defectModel.clear()
        currentDefectDictModel.clear()
        currentUnShowDefectDictModel.clear()
        defectDict={}
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

}
