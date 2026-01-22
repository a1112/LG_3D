import QtQuick
import QtQuick.Controls.Material
import "../Model/server"
QtObject {

    property var coilData

    property int coilId: 0  // 二级ID
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

    property AlarmItemInfo alarmItemInfo_L: AlarmItemInfo{}
    property AlarmItemInfo alarmItemInfo_S: AlarmItemInfo{}

    property CoilCheck coilCheck: CoilCheck{

    }

    property var defectsData


    function checkDefectShow(fliterDict){
        for (let i=0;i<defectsData.count;i++ ){
            let item_defect =defectsData.get(i)
            // console.log("isShowDefect",Object.keys(item_defect))
            if(fliterDict[item_defect.defectName]){
                                return true
                                }
        }
        if (defectsData.length<=0){

        }
        return false

    }

    function init(coil){
        // 直接读取 model 的属性，不进行深拷贝（避免循环引用问题）
        // 注意：不修改原始数据，只读取
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

        // 存储对 model 的引用（只读，不修改）
        coilData = coil

        // 处理 AlarmInfo
        if (coil.AlarmInfo) {
            if (coil.AlarmInfo["S"]){
                alarmItemInfo_S.setAlarmInfo(coil.AlarmInfo["S"])
            }
            if (coil.AlarmInfo["L"]){
                alarmItemInfo_L.setAlarmInfo(coil.AlarmInfo["L"])
            }
        }

        // 缺陷数据（只读引用）
        defectsData = coil.childrenCoilDefect || []

        // 时间数据
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
        tool.for_list_model(defectsData,(defect)=>{
                    let defectLevel=global.defectClassProperty.getDefectLevelByDefectName(defect.defectName)
                    if (defectLevel>=defectMaxErrorLevel){
                                    if (leftCore.isShowDefect(defect.defectName)){
                                        maxDefect.init(defect)
                                    }
                                }
                            })
        return maxDefect.defectName
    }

}
