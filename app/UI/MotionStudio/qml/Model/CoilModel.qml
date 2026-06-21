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

    property DateTimeProject coilCreateTime: DateTimeProject {}
    property DateTimeProject coilDetectionTime: DateTimeProject {}

    property int coilCheckStatus: 0
    property int coilDefectCountS: 0
    property int coilDefectCountL: 0
    property int coilDefectCountTotal: coilDefectCountS + coilDefectCountL
    property int coilStatus_L: 0
    property int coilGrade: 0
    property int coilStatus_S: 0
    property string coilMsg: ""
    property bool hasCoil: true
    property string maxDefectName: ""
    property int maxDefectLevel: 0
    property string maxDefectSurface: ""

    property AlarmItemInfo alarmItemInfo_L: AlarmItemInfo {}
    property AlarmItemInfo alarmItemInfo_S: AlarmItemInfo {}

    property CoilCheck coilCheck: CoilCheck {}

    property var defectsData: []
    property DefectItemModel maxDefect: DefectItemModel {}

    property int defectMaxErrorLevel: maxDefect.defectLevel
    property color defectErrorColor: {
        if (defectMaxErrorLevel <= 2) {
            return Material.color(Material.LightBlue)
        } else if (defectMaxErrorLevel <= 3) {
            return Material.color(Material.Yellow)
        } else if (defectMaxErrorLevel <= 4) {
            return Material.color(Material.Orange)
        }
        return Material.color(Material.Red)
    }

    function _normalizeDefectsData(source) {
        if (!source) {
            return []
        }
        if (Array.isArray(source)) {
            return source
        }
        if (typeof source.length === "number") {
            let items = []
            for (let i = 0; i < source.length; i++) {
                if (typeof source.get === "function") {
                    items.push(source.get(i))
                } else {
                    items.push(source[i])
                }
            }
            return items
        }
        if (typeof source === "object") {
            return [source]
        }
        return []
    }

    function _getDefectLevel(defect) {
        if (!defect) {
            return 0
        }
        let level = _firstNumber(defect, ["defectLevel", "DefectLevel", "level", "Level"], 0)
        if (level > 0) {
            return level
        }
        let defectName = _getDefectName(defect)
        if (defectName) {
            return global.defectClassProperty.getDefectLevelByDefectName(defectName)
        }
        return 0
    }

    function _firstValue(source, keys, defaultValue) {
        if (!source) {
            return defaultValue
        }
        for (let i = 0; i < keys.length; i++) {
            let key = keys[i]
            if (source[key] !== undefined && source[key] !== null) {
                return source[key]
            }
        }
        return defaultValue
    }

    function _firstNumber(source, keys, defaultValue) {
        let value = _firstValue(source, keys, defaultValue)
        let numberValue = Number(value)
        return isFinite(numberValue) ? numberValue : defaultValue
    }

    function _getDefectName(defect) {
        return _firstValue(defect, [
            "defectName",
            "DefectName",
            "configDefectName",
            "ConfigDefectName",
            "name",
            "Name"
        ], "")
    }

    function _getDefectSurface(defect) {
        return _firstValue(defect, ["surface", "Surface"], "")
    }

    function checkDefectShow(fliterDict) {
        let items = _normalizeDefectsData(defectsData)
        for (let i = 0; i < items.length; i++) {
            let defect = items[i]
            let defectName = _getDefectName(defect)
            if (defectName && fliterDict[defectName]) {
                return true
            }
        }
        return false
    }

    function init(coil) {
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
        let normalizedDefects = _normalizeDefectsData(coil.childrenCoilDefect || coil.defects)
        coilDefectCountS = coil.DefectCountS !== undefined ? Number(coil.DefectCountS) : 0
        coilDefectCountL = coil.DefectCountL !== undefined ? Number(coil.DefectCountL) : 0
        if (coilDefectCountS + coilDefectCountL <= 0 && normalizedDefects.length > 0) {
            coilDefectCountS = normalizedDefects.length
            coilDefectCountL = 0
        }
        coilStatus_L = coil.Status_L || 0
        coilGrade = coil.Grade || 0
        coilStatus_S = coil.Status_S || 0
        coilMsg = coil.Msg || ""
        nextInfo = coil.NextInfo || ""
        nextCode = coil.NextCode || ""
        hasCoil = coil.hasCoil || false
        maxDefectName = _firstValue(coil, ["maxDefectName", "MaxDefectName"], "")
        maxDefectLevel = _firstNumber(coil, ["maxDefectLevel", "MaxDefectLevel"], 0)
        maxDefectSurface = _firstValue(coil, ["maxDefectSurface", "MaxDefectSurface"], "")

        coilData = coil

        if (coil.AlarmInfo) {
            if (coil.AlarmInfo["S"]) {
                alarmItemInfo_S.setAlarmInfo(coil.AlarmInfo["S"])
            }
            if (coil.AlarmInfo["L"]) {
                alarmItemInfo_L.setAlarmInfo(coil.AlarmInfo["L"])
            }
        }

        defectsData = normalizedDefects
        if (!maxDefectName && defectsData.length > 0) {
            maxDefectName = _getDefectName(defectsData[0])
        }
        if (maxDefectLevel <= 0 && defectsData.length > 0) {
            maxDefectLevel = _getDefectLevel(defectsData[0])
        }
        if (!maxDefectSurface && defectsData.length > 0) {
            maxDefectSurface = _getDefectSurface(defectsData[0])
        }

        coilCreateTime.initByDict(coil.CreateTime)
        coilDetectionTime.initByDict(coil.DetectionTime)

        initMaxLevelDefect()
        coilCheck.init(coil.childrenCoilCheck || [])
    }

    function getDefectNameList() {
        return _getDefectNameList_(defectsData)
    }

    function _getDefectNameList_(defectItems) {
        let nameList = []
        let items = _normalizeDefectsData(defectItems)
        items.forEach((value) => {
            let defectName = _getDefectName(value)
            if (defectName) {
                nameList.push(defectName)
            }
        })
        return nameList
    }

    function initMaxLevelDefect() {
        let foundDefect = null
        let maxLevel = -1
        let items = _normalizeDefectsData(defectsData)

        for (let i = 0; i < items.length; i++) {
            let defect = items[i]
            if (!defect) {
                continue
            }

            let level = _getDefectLevel(defect)
            if (level > maxLevel) {
                maxLevel = level
                foundDefect = defect
            }
        }

        if (foundDefect) {
            maxDefect.init(foundDefect)
            maxDefectName = _getDefectName(foundDefect) || maxDefectName
            maxDefectLevel = _getDefectLevel(foundDefect)
            maxDefectSurface = _getDefectSurface(foundDefect) || maxDefectSurface
        } else {
            maxDefect.init(null)
        }
        return maxDefect.defectName
    }
}
