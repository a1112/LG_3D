import QtQuick
import QtQuick.Controls.Material
import "../Model/server"
QtObject {

    property var coilData

    property int coilId: 0
    property string coilNo: ""
    property string coilType: ""
    property string coilInside: ""
    property string coilDia: ""
    property string coilThickness: ""
    property string coilWidth: ""
    property string coilWeight: ""
    property string coilActWidth: ""
    property string coilToNext: ""
    property string nextCode: "0"
    property string nextInfo: ""

    property DateTimeProject coilCreateTime: DateTimeProject{}
    property DateTimeProject coilDetectionTime: DateTimeProject{}

    property int coilCheckStatus: 0
    property int coilDefectCountS: 0
    property int coilDefectCountL: 0
    property int coilStatus_L: 0
    property int coilGrade: 0
    property int coilStatus_S: 0
    property string coilMsg: ""
    property bool hasCoil: true
    property string maxDefectName: ""
    property int maxDefectLevel: 0

    property AlarmItemInfo alarmItemInfo_L: AlarmItemInfo{}
    property AlarmItemInfo alarmItemInfo_S: AlarmItemInfo{}

    property CoilCheck coilCheck: CoilCheck{

    }

    property var defectsData

    function checkDefectShow(fliterDict){
        for (let i=0;i<defectsData.count;i++ ){
            let item_defect =defectsData.get(i)
            if(fliterDict[item_defect.defectName]){
                                return true
                                }
        }
        if (defectsData.length<=0){

        }
        return false

    }

    function init(coil){
        if (!coil) {
            return
        }

        coilId = coil.Id || 0
        coilNo = coil.CoilNo || ""
        coilType = coil.CoilType || ""
        coilInside = coil.CoilInside || ""
        coilDia = coil.CoilDia || ""
        coilThickness = coil.Thickness || ""
        coilWidth = coil.Width || ""
        coilWeight = coil.Weight || ""
        coilActWidth = coil.ActWidth || ""
        coilCheckStatus = coil.CheckStatus || 0
        coilDefectCountS = coil.DefectCountS || 0
        coilDefectCountL = coil.DefectCountL || 0
        coilStatus_L = coil.Status_L || 0
        coilGrade = coil.Grade || 0
        coilStatus_S = coil.Status_S || 0
        coilMsg = coil.Msg || ""
        nextInfo = coil.NextInfo || ""
        nextCode = coil.NextCode || ""
        hasCoil = coil.hasCoil || false
        maxDefectName = coil.maxDefectName || ""
        maxDefectLevel = coil.maxDefectLevel || 0

        coilData = coil

        if (coil.AlarmInfo) {
            if (coil.AlarmInfo["S"]){
                alarmItemInfo_S.setAlarmInfo(coil.AlarmInfo["S"])
            }
            if (coil.AlarmInfo["L"]){
                alarmItemInfo_L.setAlarmInfo(coil.AlarmInfo["L"])
            }
        }

        // 缺陷数据处理：确保是数组格式
        if (coil.childrenCoilDefect && coil.childrenCoilDefect.length) {
            console.log("[CoilModel.init] childrenCoilDefect type:", typeof coil.childrenCoilDefect, "length:", coil.childrenCoilDefect.length)
            console.log("[CoilModel.init] childrenCoilDefect first item:", coil.childrenCoilDefect[0])
            console.log("[CoilModel.init] childrenCoilDefect JSON:", JSON.stringify(coil.childrenCoilDefect))
            defectsData = coil.childrenCoilDefect
        } else if (coil.childrenCoilDefect && typeof coil.childrenCoilDefect === 'object') {
            console.log("[CoilModel.init] childrenCoilDefect is single object, wrapping in array")
            defectsData = [coil.childrenCoilDefect]
        } else {
            console.log("[CoilModel.init] childrenCoilDefect is null/undefined/empty, using empty array")
            defectsData = []
        }

        coilCreateTime.initByDict(coil.CreateTime)
        coilDetectionTime.initByDict(coil.DetectionTime)

        initMaxLevelDefect()
        coilCheck.init(coil.childrenCoilCheck || [])
    }

    function getDefectNameList(){
        return _getDefectNameList_(coilData)
    }

    function _getDefectNameList_(list_model){
        let name_list = []
        tool.for_list_model(list_model.defects,(value)=>{
                                name_list.push(value.defectName)
                            })
        return name_list
    }
    property DefectItemModel maxDefect: DefectItemModel{}

    property int defectMaxErrorLevel:maxDefect.defectLevel
    property color defectErrorColor:{
        if (defectMaxErrorLevel<=2){
            return Material.color(Material.LightBlue)
            }
        else if (defectMaxErrorLevel<=3){
            return Material.color(Material.Yellow)
            }
        else if (defectMaxErrorLevel<=4){
            return Material.color(Material.Orange)
            }
        else{
            return Material.color(Material.Red)
        }
    }

    function initMaxLevelDefect(){
        let foundDefect = null
        let maxLevel = -1

        // 遍历所有缺陷，找到等级最高的

        if (defectsData && defectsData.length > 0) {
                    console.log(defectsData)
            for (let i = 0; i < defectsData.length; i++) {
                let defect = null
                if (typeof defectsData.get === 'function') {
                    defect = defectsData.get(i)
                } else {
                    defect = defectsData[i]
                }

                if (!defect) continue

                // 获取缺陷等级
                let level = defect.defectLevel || 0
                // 如果没有 defectLevel，从配置获取
                console.log("defect.defectName",defect.defectName)
                if (!defect.defectLevel && defect.defectName) {
                    level = global.defectClassProperty.getDefectLevelByDefectName(defect.defectName)
                }

                // 找到最高等级的缺陷
                if (level > maxLevel) {
                    maxLevel = level
                    foundDefect = defect
                }
            }
        }
        console.log("foundDefect ",foundDefect)
        if (foundDefect) {
            maxDefect.init(foundDefect)
        } else {
            // 没有缺陷时，不调用 init（保持默认空值）
            // 或者可以调用 maxDefect.init({}) 来重置
        }
        return maxDefect.defectName
    }

}
