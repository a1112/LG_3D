import QtQuick

Item {
    property int app_index: app_core.appIndex
    property ListModel currentListModel: defectCoreModel.currentListModel
    property string lastRangeKey: ""
    property bool loading: false
    property bool refreshQueued: false
    property int requestGeneration: 0

    onApp_indexChanged: requestRefresh()
    Connections {
        target: defectCoreModel
        function onCurrentListStartIndexChanged() { requestRefresh() }
        function onCurrentListEndIndexChanged() { requestRefresh() }
    }

    Timer {
        id: refreshTimer
        interval: 120
        repeat: false
        onTriggered: flush_defects()
    }

    function requestRefresh() {
        refreshTimer.restart()
    }

    function flush_defects() {
        if (!currentListModel || currentListModel.count <= 0) {
            requestGeneration += 1
            loading = false
            refreshQueued = false
            defectCoreModel.setDefectJson([])
            lastRangeKey = ""
            return
        }

        let startId = defectCoreModel.currentListStartIndex
        let endId = defectCoreModel.currentListEndIndex
        let rangeKey = `${startId}_${endId}`

        if (loading) {
            refreshQueued = true
            return
        }
        if (rangeKey === lastRangeKey) {
            return
        }

        loading = true
        requestGeneration += 1
        let generation = requestGeneration
        api.getDefectsByCoilId(
            startId,
            endId,
            (text) => {
                if (generation !== requestGeneration) {
                    return
                }
                loading = false
                try {
                    defectCoreModel.setDefectJson(JSON.parse(text))
                    lastRangeKey = rangeKey
                } catch (error) {
                    console.warn("defect response parse failed:", error)
                }
                if (refreshQueued) {
                    refreshQueued = false
                    Qt.callLater(flush_defects)
                }
            },
            (err) => {
                if (generation !== requestGeneration) {
                    return
                }
                loading = false
                console.warn("defect refresh failed:", err)
                if (refreshQueued) {
                    refreshQueued = false
                    Qt.callLater(flush_defects)
                }
            }
        )
    }
}
