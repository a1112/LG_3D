import QtQuick
import "../Model/server"
import "../Base"

Item {
    id: root

    property var defectDictData: { return {} }
    property ListModel defectDictModel: ListModel {
        dynamicRoles: true
    }

    property string unDefectClassItemName: qsTr("无缺陷")

    property DefectClassItemModel defaultDefectClass: DefectClassItemModel {
    }
    property DefectClassItemModel unDefectClassItemModel: DefectClassItemModel {
        defectName: root.unDefectClassItemName
        defectLevel: 0
        defectColor: coreStyle.labelColor
    }

    property var defectDictAll: { return {} }
    property var defecShowTabel: defectDictAll
    property bool defeftDrawShowLasbel: true

    SettingsBase {
        property alias defeftDrawShowLasbel: root.defeftDrawShowLasbel
    }

    function flushDefectDictAll() {
        let temp = defectDictAll
        defectDictAll = {}
        defectDictAll = temp
    }

    function is_defect_show(value) {
        return value === true || value === "true"
    }

    function is_area_defect_name(defectName) {
        return defectName !== undefined
                && defectName !== null
                && defectName.indexOf("2D_") === 0
    }

    function shared_defect_name(defectName) {
        if (defectName === undefined || defectName === null) {
            return ""
        }
        let name = String(defectName)
        if (is_area_defect_name(name)) {
            return name.slice(3)
        }
        return name
    }

    function normalize_color(value) {
        if (value === undefined || value === null) {
            return "#FFA500"
        }
        if (typeof value === "string") {
            return value
        }
        if (value["r"] !== undefined && value["g"] !== undefined && value["b"] !== undefined) {
            return Qt.rgba(Number(value["r"]), Number(value["g"]), Number(value["b"]),
                           value["a"] === undefined ? 1 : Number(value["a"])).toString()
        }
        if (value["color"] !== undefined && value["color"] !== null) {
            return normalize_color(value["color"])
        }
        if (value["defectColor"] !== undefined && value["defectColor"] !== null) {
            return normalize_color(value["defectColor"])
        }
        return "#FFA500"
    }

    function upDefectDictModelByDefectDictData() {
        defectDictModel.clear()

        for (let key in defectDictData) {
            let value = defectDictData[key]
            let item = {}
            item["name"] = key
            item["num"] = 0
            item["level"] = value["level"]
            item["color"] = normalize_color(value["color"])
            item["show"] = is_defect_show(value["show"])
            if (item["show"]) {
                defectDictModel.append(item)
            }
        }

        for (let key in defectDictData) {
            let value = defectDictData[key]
            let item = {}
            item["name"] = key
            item["num"] = 0
            item["level"] = value["level"]
            item["color"] = normalize_color(value["color"])
            item["show"] = is_defect_show(value["show"])
            if (!item["show"]) {
                defectDictModel.append(item)
            }
        }
    }

    function normalize_defect_dict_data(data) {
        let normalized = {}
        for (let key in data) {
            if (is_area_defect_name(key)) {
                continue
            }
            let item = Object.assign({}, data[key])
            item["name"] = key
            normalized[key] = item
        }
        for (let key in data) {
            if (!is_area_defect_name(key)) {
                continue
            }
            let sharedName = shared_defect_name(key)
            if (sharedName in normalized) {
                continue
            }
            let item = Object.assign({}, data[key])
            item["name"] = sharedName
            normalized[sharedName] = item
        }
        return normalized
    }

    function setDefectDict(defectData) {
        defectDictData = normalize_defect_dict_data(defectData["data"])
        upDefectDictModelByDefectDictData()
        defaultDefectClass.init(defectData["default"])
    }

    function ensure_defect_class_item(defectName) {
        let sharedName = shared_defect_name(defectName)
        if (!sharedName || (sharedName in defectDictData)) {
            return false
        }

        let isAreaDefect = is_area_defect_name(defectName)
        let defaultLevel = defaultDefectClass.defectLevel || 1
        let defaultColor = normalize_color(defaultDefectClass.defectColor)
        let item = {
            "name": sharedName,
            "level": isAreaDefect ? defaultLevel : 1,
            "color": isAreaDefect ? defaultColor : "#FFA500",
            "show": isAreaDefect,
            "num": 0
        }

        defectDictData[sharedName] = item
        if (!(sharedName in defectDictAll)) {
            defectDictAll[sharedName] = is_defect_show(item["show"])
        }
        upDefectDictModelByDefectDictData()
        flushDefectDictAll()
        return true
    }

    function getDefectLevelByDefectName(defectName) {
        let sharedName = shared_defect_name(defectName)
        if (sharedName in defectDictData) {
            return defectDictData[sharedName]["level"] ?? defaultDefectClass.defectLevel
        }
        return 1
    }

    function getColorByName(name) {
        let sharedName = shared_defect_name(name)
        if (defectDictData[sharedName] === undefined) {
            return "#FFF"
        }
        return normalize_color(defectDictData[sharedName]["color"])
    }

    function getColorByLevel(level) {
        if (level >= 3) {
            return "red"
        }
        if (level >= 2) {
            return "yellow"
        }
        if (level >= 1) {
            return "gray"
        }
        return "#00000000"
    }

    function selecct_all_un_defect_show() {
        for (let key in defectDictData) {
            let value = defectDictData[key]
            if (!is_defect_show(value["show"])) {
                defectDictAll[value["name"]] = true
            }
        }
        coreModel.flushDefectDictAll()
    }

    function un_selecct_all_un_defect_show() {
        for (let key in defectDictData) {
            let value = defectDictData[key]
            if (!is_defect_show(value["show"])) {
                defectDictAll[value["name"]] = false
            }
        }
        coreModel.flushDefectDictAll()
    }

    function select_area_defect() {
        for (let key in defectDictData) {
            let value = defectDictData[key]
            if (is_area_defect_name(value["name"])) {
                defectDictAll[value["name"]] = true
            }
        }
        coreModel.flushDefectDictAll()
    }

    function un_select_area_defect() {
        for (let key in defectDictData) {
            let value = defectDictData[key]
            if (is_area_defect_name(value["name"])) {
                defectDictAll[value["name"]] = false
            }
        }
        coreModel.flushDefectDictAll()
    }
}
