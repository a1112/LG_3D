import QtQuick

Item {
    id: root

    property ListModel globDefectDictModel: global.defectClassProperty.defectDictModel
    property int globDefectDictModelCount: globDefectDictModel.count
    onGlobDefectDictModelCountChanged: {
        initDefectDictModel()
    }

    property ListModel defectDictModel: ListModel {}
    property ListModel currentListModel: coreModel.currentCoilListModel

    readonly property int top_: currentListModel.count ? currentListModel.get(0).Id : 0
    readonly property int end_: currentListModel.count ? currentListModel.get(currentListModel.count - 1).Id : 0

    property int currentListStartIndex: Math.min(top_, end_)
    property int currentListEndIndex: Math.max(top_, end_)

    property var defectsModelAll: ListModel {
        dynamicRoles: true
    }

    property var defectsModel: ListModel {
        dynamicRoles: true
    }

    property var defectJson: []

    function initDefectDictModel() {
        defectDictModel.clear()
        tool.for_list_model(globDefectDictModel, (item) => {
            let it = globalDefectClassItemModel.itemTodict(item)
            let cleanIt = {}
            for (let key in it) {
                if (it[key] !== null && it[key] !== undefined) {
                    cleanIt[key] = it[key]
                }
            }
            defectDictModel.append(cleanIt)
        })
        updateDefectCounts()
        filterCore.resetFilterDict()
    }

    function updateDefectCounts() {
        let counts = {}
        tool.for_list_model(defectDictModel, (item) => {
            counts[item["name"]] = 0
        })

        tool.for_list_model(defectsModelAll, (item) => {
            let name = item["defectName"]
            if (name && counts[name] !== undefined) {
                counts[name]++
            }
        })

        for (let i = 0; i < defectDictModel.count; i++) {
            let item = defectDictModel.get(i)
            item["num"] = counts[item["name"]] || 0
            defectDictModel.set(i, item)
        }
    }

    function flushModel() {
        defectsModel.clear()
        tool.for_list_model(defectsModelAll, (item) => {
            if (filterCore.itemIsShow(item)) {
                let cleanItem = {}
                for (let key in item) {
                    if (item[key] !== null && item[key] !== undefined) {
                        cleanItem[key] = item[key]
                    }
                }
                defectsModel.append(cleanItem)
            }
        })
    }

    function flushModelAll() {
        defectsModelAll.clear()

        defectJson.forEach((value) => {
            if (value !== null && value !== undefined) {
                if (global.defectClassProperty.is_area_defect_name(value.defectName)) {
                    global.defectClassProperty.ensure_defect_class_item(value.defectName)
                }
                root.defectsModelAll.append(value)
            }
        })

        updateDefectCounts()
        flushModel()
    }

    function setDefectJson(data) {
        defectJson = Array.isArray(data) ? data : []
        flushModelAll()
    }
}
