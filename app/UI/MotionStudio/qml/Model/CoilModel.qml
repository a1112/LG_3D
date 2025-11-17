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
        coilData = coil
        coilId = coil.Id
        coilNo = coil.CoilNo
        coilType = coil.CoilType
        coilInside = coil.CoilInside
        coilDia = coil.CoilDia
        coilThickness = coil.Thickness
        coilWidth = coil.Width
        coilWeight = coil.Weight
        coilActWidth = coil.ActWidth
        // coilDetectionTime = coil.DetectionTime
        // coilCreateTime = coil.CreateTime//coil.CreateTime
        coilCheckStatus = coil.CheckStatus
        coilDefectCountS = coil.DefectCountS
        coilDefectCountL = coil.DefectCountL
        coilStatus_L = coil.Status_L
        coilGrade = coil.Grade
        coilStatus_S = coil.Status_S
        coilMsg = coil.Msg
        nextInfo = coil.NextInfo
        nextCode = coil.NextCode
        for (let key in coil.AlarmInfo){
            if (key=="S"){
                alarmItemInfo_S.setAlarmInfo(coil.AlarmInfo[key])
            }
            if (key=="L"){
                alarmItemInfo_L.setAlarmInfo(coil.AlarmInfo[key])
            }
        }

        defectsData = coil.childrenCoilDefect  // 全部缺陷
        coilCreateTime.initByDict(coil.CreateTime)
        coilDetectionTime.initByDict(coil.DetectionTime)

        initMaxLevelDefect()
        coilCheck.init(coil.childrenCoilCheck)
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
