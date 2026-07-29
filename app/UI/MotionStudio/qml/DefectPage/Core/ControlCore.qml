import QtQuick

Item {
    id: root

    required property var appController
    required property var apiClient
    required property var defectModel

    readonly property int appIndex: root.appController.appIndex
    readonly property ListModel currentListModel: root.defectModel.currentListModel
    property string lastRangeKey: ""
    property bool loading: false
    property bool refreshQueued: false
    property int requestGeneration: 0

    onAppIndexChanged: root.requestRefresh()
    Connections {
        target: root.defectModel
        function onCurrentListStartIndexChanged() { root.requestRefresh() }
        function onCurrentListEndIndexChanged() { root.requestRefresh() }
    }

    Timer {
        id: refreshTimer
        interval: 120
        repeat: false
        onTriggered: root.flushDefects()
    }

    function requestRefresh() {
        refreshTimer.restart()
    }

    function forceRefresh() {
        root.lastRangeKey = ""
        root.requestRefresh()
    }

    function flushDefects() {
        if (!root.currentListModel || root.currentListModel.count <= 0) {
            root.requestGeneration += 1
            root.loading = false
            root.refreshQueued = false
            root.defectModel.setDefectJson([])
            root.lastRangeKey = ""
            return
        }

        let startId = root.defectModel.currentListStartIndex
        let endId = root.defectModel.currentListEndIndex
        let rangeKey = `${startId}_${endId}`

        if (root.loading) {
            root.refreshQueued = true
            return
        }
        if (rangeKey === root.lastRangeKey) {
            return
        }

        root.loading = true
        root.requestGeneration += 1
        let generation = root.requestGeneration
        root.apiClient.getDefectsByCoilId(
            startId,
            endId,
            (text) => {
                if (generation !== root.requestGeneration) {
                    return
                }
                root.loading = false
                try {
                    root.defectModel.setDefectJson(JSON.parse(text))
                    root.lastRangeKey = rangeKey
                } catch (error) {
                    console.warn("defect response parse failed:", error)
                }
                if (root.refreshQueued) {
                    root.refreshQueued = false
                    Qt.callLater(root.flushDefects)
                }
            },
            (err) => {
                if (generation !== root.requestGeneration) {
                    return
                }
                root.loading = false
                console.warn("defect refresh failed:", err)
                if (root.refreshQueued) {
                    root.refreshQueued = false
                    Qt.callLater(root.flushDefects)
                }
            }
        )
    }
}
