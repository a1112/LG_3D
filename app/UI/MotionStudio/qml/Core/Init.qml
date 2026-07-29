import QtQuick

Item {
    id: root

    required property var apiClient
    required property var model
    required property var coreController
    required property var globalContext
    required property var appContext

    property alias init_num: coilListController.limit
    property alias initBatchSize: coilListController.batchSize
    readonly property alias isListLoading: coilListController.loading
    readonly property alias isBootstrapLoading: bootstrapController.loading
    readonly property alias bootstrapLoaded: bootstrapController.loaded
    readonly property string lastError: coilListController.lastError
                                        || bootstrapController.lastError

    BootstrapController {
        id: bootstrapController
        apiClient: root.apiClient
        model: root.model
        appContext: root.appContext
    }

    CoilListController {
        id: coilListController
        apiClient: root.apiClient
        model: root.model
        coreController: root.coreController
    }

    function initDefectDict(defectDictData) {
        globalContext.defectClassProperty.setDefectDict(defectDictData)
    }

    function flushDefectDict() {
        apiClient.getDefectDict(function(result) {
            try {
                initDefectDict(JSON.parse(result))
            } catch (error) {
                console.warn("defect dictionary parse failed:", error)
            }
        }, function(error) {
            console.warn("defect dictionary refresh failed:", error)
        })
    }

    function refreshMetadata(force) {
        return bootstrapController.refresh(force === true)
    }

    function refreshCoils() {
        return coilListController.refresh()
    }

    function flushList(forceMetadata) {
        refreshMetadata(forceMetadata === true)
        return refreshCoils()
    }

    function refreshAll(forceMetadata) {
        flushDefectDict()
        return flushList(forceMetadata)
    }
}
