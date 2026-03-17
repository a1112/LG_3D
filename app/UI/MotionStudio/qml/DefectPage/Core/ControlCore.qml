import QtQuick

Item {
    property int app_index: app_core.appIndex
    property ListModel currentListModel: defectCoreModel.currentListModel
    property string lastRangeKey: ""
    property bool loading: false

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
            defectCoreModel.setDefectJson([])
            lastRangeKey = ""
            return
        }

        let startId = defectCoreModel.currentListStartIndex
        let endId = defectCoreModel.currentListEndIndex
        let rangeKey = `${startId}_${endId}`

        if (loading || rangeKey === lastRangeKey) {
            return
        }

        loading = true
        api.getDefectsByCoilId(
            startId,
            endId,
            (text) => {
                lastRangeKey = rangeKey
                loading = false
                defectCoreModel.setDefectJson(JSON.parse(text))
            },
            (err) => {
                loading = false
                console.log("flush_defects error", err)
            }
        )
    }
}
