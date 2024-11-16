import QtQuick 2.15

Item {
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
    property var coilTime:new Date()
    property string coilTimeString:Qt.formatDateTime(coilTime,"yyyy_MM_dd hh_mm_ss")
    property var coilCreateTime: {return []}

    property var dataString:Qt.formatDateTime(coilTime,"yyyy年MM月dd日")
    property var timeString:Qt.formatDateTime(coilTime,"hh点mm分ss秒")

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
        coilCreateTime = coil.CreateTime
        coilCheckStatus = coil.CheckStatus
        coilDefectCountS = coil.DefectCountS
        coilDefectCountL = coil.DefectCountL
        coilStatus_L = coil.Status_L
        coilGrade = coil.Grade
        coilStatus_S = coil.Status_S
        coilMsg = coil.Msg
        nextInfo = coil.NextInfo
        nextCode = coil.NextCode

        coilTime = new Date(coilCreateTime["year"],coilCreateTime["month"]-1,coilCreateTime["day"],
                            coilCreateTime["hour"],coilCreateTime["minute"],coilCreateTime["second"])


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
