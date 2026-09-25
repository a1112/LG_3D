import QtQuick

Item {
    id: root

    required property var modelStore
    required property var globalContext
    required property var toolService
    required property var classItemConverter
    required property var filterController

    readonly property ListModel globDefectDictModel: root.globalContext.defectClassProperty.defectDictModel
    readonly property int globDefectDictModelCount: root.globDefectDictModel.count
    onGlobDefectDictModelCountChanged: {
        root.initDefectDictModel()
    }

    property ListModel defectDictModel: ListModel {
        dynamicRoles: true
    }
    readonly property ListModel currentListModel: root.modelStore.currentCoilListModel

    readonly property int top_: root.currentListModel.count ? root.currentListModel.get(0).Id : 0
    readonly property int end_: root.currentListModel.count
                                ? root.currentListModel.get(root.currentListModel.count - 1).Id : 0

    readonly property int currentListStartIndex: Math.min(root.top_, root.end_)
    readonly property int currentListEndIndex: Math.max(root.top_, root.end_)

    property var defectsModelAll: ListModel {
        dynamicRoles: true
    }

    property var defectsModel: ListModel {
        dynamicRoles: true
    }

    property var defectJson: []

    function initDefectDictModel() {
        root.defectDictModel.clear()
        root.toolService.for_list_model(root.globDefectDictModel, (item) => {
            let it = root.classItemConverter.itemTodict(item)
            let cleanIt = {}
            for (let key in it) {
                if (it[key] !== null && it[key] !== undefined) {
                    cleanIt[key] = it[key]
                }
            }
            root.defectDictModel.append(cleanIt)
        })
        root.updateDefectCounts()
        root.filterController.resetFilterDict()
    }

    function updateDefectCounts() {
        let counts = {}
        root.toolService.for_list_model(root.defectDictModel, (item) => {
            counts[item["name"]] = 0
        })

        root.toolService.for_list_model(root.defectsModelAll, (item) => {
            let name = root.globalContext.defectClassProperty.shared_defect_name(item["defectName"])
            if (name && counts[name] !== undefined) {
                counts[name]++
            }
        })

        for (let i = 0; i < root.defectDictModel.count; i++) {
            let item = root.defectDictModel.get(i)
            item["num"] = counts[item["name"]] || 0
            root.defectDictModel.set(i, item)
        }
    }

    function flushModel() {
        root.defectsModel.clear()
        root.toolService.for_list_model(root.defectsModelAll, (item) => {
            if (root.filterController.itemIsShow(item)) {
                let cleanItem = {}
                for (let key in item) {
                    if (item[key] !== null && item[key] !== undefined) {
                        cleanItem[key] = item[key]
                    }
                }
                root.defectsModel.append(cleanItem)
            }
        })
    }

    function flushModelAll() {
        root.defectsModelAll.clear()

        root.defectJson.forEach((value) => {
            if (value !== null && value !== undefined) {
                if (root.globalContext.defectClassProperty.is_area_defect_name(value.defectName)) {
                    root.globalContext.defectClassProperty.ensure_defect_class_item(value.defectName)
                }
                value.configDefectName =
                        root.globalContext.defectClassProperty.shared_defect_name(value.defectName)
                root.defectsModelAll.append(value)
            }
        })

        root.updateDefectCounts()
        root.flushModel()
    }

    function setDefectJson(data) {
        root.defectJson = Array.isArray(data) ? data : []
        root.flushModelAll()
    }
}
