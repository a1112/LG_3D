import QtQuick

QtObject {
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


    function setCoil(coil){
        coilId = coil.SecondaryCoilId
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
        coilCreateTime.initByDict(coil.CreateTime)
        coilDetectionTime.initByDict(coil.DetectionTime)
        for (let key in coil.AlarmInfo){
            if (key=="S"){
                alarmItemInfo_S.setAlarmInfo(coil.AlarmInfo[key])
            }
            if (key=="L"){
                alarmItemInfo_L.setAlarmInfo(coil.AlarmInfo[key])
            }

        }
    }

}
