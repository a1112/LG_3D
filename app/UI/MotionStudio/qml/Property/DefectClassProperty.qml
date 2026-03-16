import QtQuick
import "../Model/server"
import "../Base"

Item {
    id: root

    property var defectDictData: { return {} }
    property ListModel defectDictModel: ListModel {
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

    function upDefectDictModelByDefectDictData() {
        defectDictModel.clear()

        for (let key in defectDictData) {
            let value = defectDictData[key]
            let item = {}
            item["name"] = key
            item["num"] = 0
            item["level"] = value["level"]
            item["color"] = value["color"]
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
            item["color"] = value["color"]
            item["show"] = is_defect_show(value["show"])
            if (!item["show"]) {
                defectDictModel.append(item)
            }
        }
    }

    function setDefectDict(defectData) {
        defectDictData = defectData["data"]
        upDefectDictModelByDefectDictData()
        defaultDefectClass.init(defectData["default"])
    }

    function ensure_defect_class_item(defectName) {
        if (!defectName || (defectName in defectDictData)) {
            return false
        }

        let isAreaDefect = is_area_defect_name(defectName)
        let defaultLevel = defaultDefectClass.defectLevel || 1
        let defaultColor = defaultDefectClass.defectColor || "#FFA500"
        let item = {
            "name": defectName,
            "level": isAreaDefect ? defaultLevel : 1,
            "color": isAreaDefect ? defaultColor : "#FFA500",
            "show": isAreaDefect,
            "num": 0
        }

        defectDictData[defectName] = item
        if (!(defectName in defectDictAll)) {
            defectDictAll[defectName] = is_defect_show(item["show"])
        }
        upDefectDictModelByDefectDictData()
        flushDefectDictAll()
        return true
    }

    function getDefectLevelByDefectName(defectName) {
        if (defectName in defectDictData) {
            return defectDictData[defectName]["level"] ?? defaultDefectClass.defectLevel
        }
        return 1
    }

    function getColorByName(name) {
        if (defectDictData[name] === undefined) {
            return "#FFF"
        }
        return defectDictData[name]["color"]
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
